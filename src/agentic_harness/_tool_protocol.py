"""ToolProtocol v1: closed, deterministic agent-callable tool surface.

The registry in ``contracts/tool_protocol/registry.yaml`` is authoritative for
names and profiles.  This module owns validation, deterministic effect/resource
calculation, safe process invocation, and atomic filesystem/PatchSet helpers.
"""

from __future__ import annotations

import os
import hashlib
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable

import yaml
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictBytes, StrictInt, StrictStr, field_validator

from ._canonical import digest_for
from ._contracts import find_contracts_root
from ._resource_normalization import normalize_repo_path


class ToolProtocolError(ValueError):
    pass


class ToolStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    DENIED = "DENIED"
    BLOCKED_CAPABILITY = "BLOCKED_CAPABILITY"
    STALE_PRECONDITION = "STALE_PRECONDITION"


class Atomicity(StrEnum):
    READ_ONLY = "READ_ONLY"
    SINGLE_RESOURCE_ATOMIC = "SINGLE_RESOURCE_ATOMIC"
    JOURNALED_MULTI_RESOURCE = "JOURNALED_MULTI_RESOURCE"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=False)


class NormalizedResource(StrictModel):
    kind: StrictStr
    normalized_key: StrictStr


class ToolError(StrictModel):
    code: StrictStr
    category: StrictStr
    message: StrictStr
    retryable: StrictBool
    details: dict[str, Any]


class InlineOutput(StrictModel):
    text: StrictStr
    byte_length: StrictInt
    media_type: StrictStr = "text/plain; charset=utf-8"


class ArtifactOutput(StrictModel):
    digest: StrictStr
    byte_length: StrictInt
    media_type: StrictStr
    preview: StrictStr


Output = InlineOutput | ArtifactOutput


class ToolRequest(StrictModel):
    tool_call_id: StrictStr
    run_id: StrictStr
    tool_name: StrictStr
    tool_version: StrictInt
    tool_schema_digest: StrictStr
    arguments: dict[str, Any]
    argument_digest: StrictStr
    requested_effects: set[StrictStr]
    requested_resources: list[NormalizedResource]
    expected_candidate_snapshot: StrictStr | None = None
    timeout_ms: StrictInt | None = Field(default=None, ge=1)

    @field_validator("tool_name")
    @classmethod
    def nonempty_name(cls, value: str) -> str:
        if not value:
            raise ValueError("tool_name must not be empty")
        return value


class ToolResult(StrictModel):
    tool_call_id: StrictStr
    status: ToolStatus
    started_at: datetime
    finished_at: datetime
    exit_code: StrictInt | None = None
    stdout: Output | None = None
    stderr: Output | None = None
    artifacts: list[StrictStr] = Field(default_factory=list)
    pre_candidate_snapshot: StrictStr | None = None
    post_candidate_snapshot: StrictStr | None = None
    error: ToolError | None = None


class PatchOperation(StrictModel):
    operation: StrictStr
    path: StrictStr | None = None
    from_path: StrictStr | None = None
    preimage_digest: StrictStr | None = None
    postimage_digest: StrictStr | None = None
    content: StrictBytes | None = None
    expected_mode: StrictInt | None = None
    new_mode: StrictInt | None = None


class PatchSet(StrictModel):
    base_snapshot: StrictStr
    operations: list[PatchOperation] = Field(min_length=1)


class ToolDefinition(StrictModel):
    tool_name: StrictStr
    tool_version: StrictInt
    request_schema_ref: StrictStr
    result_schema_ref: StrictStr
    error_codes: list[StrictStr]
    effect_calculator: StrictStr
    resource_calculator: StrictStr
    atomicity: Atomicity
    cancellation_profile: StrictStr
    output_limit_profile: StrictStr


def _registry_path() -> Path:
    root = find_contracts_root()
    if root is None:
        raise ToolProtocolError("contracts/ root unavailable; tool authority is unavailable")
    path = root / "tool_protocol" / "registry.yaml"
    if not path.is_file():
        raise ToolProtocolError("ToolProtocol registry is unavailable")
    return path


def load_tool_registry() -> dict[str, ToolDefinition]:
    raw = yaml.safe_load(_registry_path().read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("x-contract-name") != "ToolProtocol":
        raise ToolProtocolError("malformed ToolProtocol registry")
    entries = raw.get("tools")
    if not isinstance(entries, list):
        raise ToolProtocolError("ToolProtocol registry tools must be a list")
    parsed = [ToolDefinition.model_validate(entry) for entry in entries]
    result = {entry.tool_name: entry for entry in parsed}
    if len(result) != len(parsed):
        raise ToolProtocolError("duplicate tool name in ToolProtocol registry")
    return result


def registered_tool(name: str) -> ToolDefinition:
    definition = load_tool_registry().get(name)
    if definition is None:
        raise ToolProtocolError(f"unknown tool {name!r}; unregistered tools fail closed")
    return definition


def tool_schema_digest(name: str) -> str:
    definition = registered_tool(name)
    return digest_for(definition.model_dump(mode="json"))


def validate_request(request: ToolRequest) -> ToolDefinition:
    definition = registered_tool(request.tool_name)
    if request.tool_version != definition.tool_version:
        raise ToolProtocolError("tool version does not match the registered version")
    if request.tool_schema_digest != tool_schema_digest(request.tool_name):
        raise ToolProtocolError("tool schema digest does not match the registry")
    if request.argument_digest != digest_for(request.arguments):
        raise ToolProtocolError("argument digest does not match arguments")
    return definition


def _path_resource(root: Path, value: str) -> NormalizedResource:
    return NormalizedResource(kind="repo_path", normalized_key=normalize_repo_path(value, root=root))


def calculate_effects(tool_name: str, arguments: dict[str, Any]) -> frozenset[str]:
    registered_tool(tool_name)
    if tool_name in {"fs.stat", "fs.list", "fs.read_bytes", "fs.read_text", "search.literal", "search.regex", "search.glob", "git.status", "git.diff", "git.show", "git.rev_parse", "git.ls_files"}:
        return frozenset({"READ"})
    if tool_name in {"fs.write_file", "fs.mkdir", "fs.rename", "fs.delete", "patch.apply", "git.add", "git.commit", "git.worktree_create", "git.worktree_remove", "git.apply_candidate_integration"}:
        return frozenset({"WORKSPACE_WRITE"})
    if tool_name == "process.run":
        if arguments.get("shell", False):
            raise ToolProtocolError("TOOL_SHELL_INTERPRETATION_REQUIRES_REGISTERED_SHELL_TOOL")
        return frozenset({"PROCESS_EXEC"})
    raise ToolProtocolError(f"no authoritative effect calculator for {tool_name!r}")


def calculate_resources(tool_name: str, arguments: dict[str, Any], *, root: Path) -> tuple[NormalizedResource, ...]:
    registered_tool(tool_name)
    values: list[NormalizedResource] = []
    for key in ("path", "source", "destination", "cwd"):
        value = arguments.get(key)
        if isinstance(value, str) and key != "cwd":
            values.append(_path_resource(root, value))
    if tool_name.startswith("search."):
        for value in arguments.get("roots", []):
            if isinstance(value, str):
                values.append(_path_resource(root, value))
    if tool_name == "process.run":
        executable = arguments.get("executable", "")
        cwd = arguments.get("cwd", "")
        argv = arguments.get("argv", [])
        values.append(NormalizedResource(kind="process", normalized_key=f"{executable}\u0000{cwd}\u0000{digest_for(argv)}"))
    unique: dict[tuple[str, str], NormalizedResource] = {}
    for resource in values:
        unique.setdefault((resource.kind, resource.normalized_key), resource)
    return tuple(unique.values())


def _redact(data: bytes, secret_values: tuple[bytes, ...]) -> bytes:
    for secret in secret_values:
        if secret:
            data = data.replace(secret, b"[REDACTED]")
    return data


def _output(data: bytes, *, limit: int, media_type: str = "text/plain; charset=utf-8") -> Output:
    if len(data) <= limit:
        return InlineOutput(text=data.decode("utf-8", errors="replace"), byte_length=len(data), media_type=media_type)
    digest = content_digest(data)
    preview = data[:limit].decode("utf-8", errors="replace")
    return ArtifactOutput(digest=digest, byte_length=len(data), media_type=media_type, preview=preview)


def execute_process(*, executable: str, argv: list[str], cwd: Path, env: dict[str, str], timeout_ms: int | None = None, stdin: bytes | None = None, output_limit: int = 65536, cancel: Callable[[], bool] | None = None, secret_values: tuple[str, ...] = ()) -> ToolResult:
    """Run exact argv with a controlled environment and no shell."""
    started = datetime.now(timezone.utc)
    proc: subprocess.Popen[bytes] | None = None
    try:
        proc = subprocess.Popen([executable, *argv], cwd=str(cwd), env=dict(env), stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, start_new_session=True)
        deadline = None if timeout_ms is None else time.monotonic() + timeout_ms / 1000
        while proc.poll() is None:
            if cancel and cancel():
                _terminate_process_tree(proc)
                return _process_result(proc, ToolStatus.CANCELLED, started, output_limit, secret_values=secret_values, code="TOOL_CANCELLED")
            if deadline is not None and time.monotonic() >= deadline:
                _terminate_process_tree(proc)
                return _process_result(proc, ToolStatus.TIMEOUT, started, output_limit, secret_values=secret_values, code="TOOL_TIMEOUT")
            time.sleep(0.01)
        stdout, stderr = proc.communicate(input=stdin)
        return _process_result(proc, ToolStatus.SUCCESS if proc.returncode == 0 else ToolStatus.FAILURE, started, output_limit, stdout, stderr, secret_values=secret_values)
    except OSError as exc:
        return ToolResult(tool_call_id="process.run", status=ToolStatus.FAILURE, started_at=started, finished_at=datetime.now(timezone.utc), error=ToolError(code="TOOL_PROCESS_ERROR", category="PROCESS", message=str(exc), retryable=False, details={}))


def _terminate_process_tree(proc: subprocess.Popen[bytes]) -> None:
    try:
        if os.name == "nt":
            proc.terminate()
        else:
            os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        proc.kill()


def _process_result(proc: subprocess.Popen[bytes], status: ToolStatus, started: datetime, limit: int, stdout: bytes = b"", stderr: bytes = b"", *, secret_values: tuple[str, ...] = (), code: str | None = None) -> ToolResult:
    if proc.poll() is None:
        stdout, stderr = proc.communicate()
    error = None if status == ToolStatus.SUCCESS else ToolError(code=code or "TOOL_PROCESS_FAILED", category="PROCESS", message="process did not complete successfully", retryable=status == ToolStatus.TIMEOUT, details={})
    secrets = tuple(value.encode("utf-8") for value in secret_values)
    return ToolResult(tool_call_id="process.run", status=status, started_at=started, finished_at=datetime.now(timezone.utc), exit_code=proc.returncode, stdout=_output(_redact(stdout, secrets), limit=limit), stderr=_output(_redact(stderr, secrets), limit=limit), error=error)


def atomic_write(root: Path, relative_path: str, content: bytes, *, expected_preimage_digest: str | None = None) -> str:
    normalized = normalize_repo_path(relative_path, root=root)
    target = (root / Path(normalized)).resolve(strict=False)
    if target.exists() and target.is_symlink():
        raise ToolProtocolError("TOOL_PATH_SYMLINK_ESCAPE")
    current = target.read_bytes() if target.exists() else None
    current_digest = content_digest(current) if current is not None else content_digest(b"")
    if expected_preimage_digest is not None and current_digest != expected_preimage_digest:
        raise ToolProtocolError("TOOL_STALE_PRECONDITION")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".harness-write-", dir=str(target.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return content_digest(content)


def content_digest(content: bytes) -> str:
    """Digest raw file bytes; canonical serialization remains for structured objects."""
    return "sha256:" + hashlib.sha256(content).hexdigest()


def apply_patch_set(root: Path, patch_set: PatchSet) -> tuple[str, ...]:
    """Validate every PatchSet operation before mutation and roll back on failure."""
    plans: list[tuple[str, Path, Path | None, bytes | None, int | None]] = []
    seen: set[str] = set()
    for op in patch_set.operations:
        if op.operation not in {"CreateFile", "ModifyFile", "DeleteFile", "RenameFile", "SetExecutable"}:
            raise ToolProtocolError("TOOL_INVALID_PATCH_OPERATION")
        if op.path is None and op.operation != "RenameFile":
            raise ToolProtocolError("TOOL_INVALID_PATCH_OPERATION")
        path = normalize_repo_path(op.path or op.from_path or "", root=root)
        if path in seen:
            raise ToolProtocolError("TOOL_PATCH_DUPLICATE_PATH")
        seen.add(path)
        target = (root / path).resolve(strict=False)
        if target.exists() and target.is_symlink():
            raise ToolProtocolError("TOOL_PATH_SYMLINK_ESCAPE")
        current = target.read_bytes() if target.exists() else None
        if op.operation == "CreateFile" and current is not None:
            raise ToolProtocolError("TOOL_STALE_PRECONDITION")
        if op.operation in {"ModifyFile", "DeleteFile", "RenameFile"} and op.preimage_digest is None:
            raise ToolProtocolError("TOOL_INVALID_PATCH_OPERATION")
        if op.operation in {"ModifyFile", "DeleteFile", "RenameFile"} and current is None:
            raise ToolProtocolError("TOOL_STALE_PRECONDITION")
        if op.preimage_digest is not None and content_digest(current or b"") != op.preimage_digest:
            raise ToolProtocolError("TOOL_STALE_PRECONDITION")
        if op.operation in {"CreateFile", "ModifyFile"}:
            if op.content is None or (op.postimage_digest is not None and content_digest(op.content) != op.postimage_digest):
                raise ToolProtocolError("TOOL_INVALID_PATCH_OPERATION")
        plans.append((op.operation, target, None, op.content, op.new_mode))

    backups: dict[Path, bytes | None] = {target: (target.read_bytes() if target.exists() else None) for _, target, _, _, _ in plans}
    try:
        for operation, target, _, content, mode in plans:
            if operation in {"CreateFile", "ModifyFile"}:
                target.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(root, target.relative_to(root).as_posix(), content or b"")
            elif operation == "DeleteFile":
                target.unlink()
            elif operation == "SetExecutable":
                if mode is None:
                    raise ToolProtocolError("TOOL_INVALID_PATCH_OPERATION")
                os.chmod(target, mode)
            else:
                raise ToolProtocolError("TOOL_PATCH_RENAME_UNSUPPORTED")
    except Exception:
        for target, original in backups.items():
            if original is None:
                if target.exists():
                    target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(original)
        raise
    return tuple(path for path in seen)


_GIT_NETWORK_COMMANDS = frozenset({"fetch", "pull", "push", "clone", "remote", "submodule"})
_GIT_COMMANDS = frozenset({"status", "diff", "show", "rev-parse", "ls-files", "add", "commit", "worktree"})


def build_git_argv(operation: str, args: list[str], *, repo_root: Path) -> list[str]:
    """Build a fixed, hook/filter-sanitized Git argv; network is never exposed."""
    if operation in _GIT_NETWORK_COMMANDS or operation not in _GIT_COMMANDS:
        raise ToolProtocolError("TOOL_GIT_OPERATION_NOT_ALLOWED")
    if any("\x00" in arg or arg in {"--upload-pack", "--config-env"} for arg in args):
        raise ToolProtocolError("TOOL_GIT_ARGUMENT_INVALID")
    command = ["git", "-C", str(repo_root), "-c", "core.hooksPath=NUL", "-c", "core.fsmonitor=false", operation]
    if operation == "worktree":
        command.extend(["--no-guess"])
    command.extend(args)
    return command


__all__ = ["Atomicity", "NormalizedResource", "PatchOperation", "PatchSet", "ToolDefinition", "ToolError", "ToolProtocolError", "ToolRequest", "ToolResult", "ToolStatus", "apply_patch_set", "atomic_write", "build_git_argv", "calculate_effects", "calculate_resources", "content_digest", "execute_process", "load_tool_registry", "registered_tool", "tool_schema_digest", "validate_request"]
