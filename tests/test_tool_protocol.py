from pathlib import Path
import sys

import pytest

from agentic_harness._canonical import digest_for
from agentic_harness._tool_protocol import (
    PatchOperation,
    PatchSet,
    ToolProtocolError,
    apply_patch_set,
    atomic_write,
    build_git_argv,
    content_digest,
    load_tool_registry,
    registered_tool,
    execute_process,
    tool_schema_digest,
)


def test_closed_registry_and_unknown_tools_fail_closed() -> None:
    registry = load_tool_registry()
    assert "fs.read_text" in registry
    assert "git.push" not in registry
    with pytest.raises(ToolProtocolError):
        registered_tool("git.push")


def test_stale_write_has_zero_mutation(tmp_path: Path) -> None:
    atomic_write(tmp_path, "value.txt", b"before")
    with pytest.raises(ToolProtocolError, match="TOOL_STALE_PRECONDITION"):
        atomic_write(tmp_path, "value.txt", b"after", expected_preimage_digest=content_digest(b"other"))
    assert (tmp_path / "value.txt").read_bytes() == b"before"


def test_patch_preflights_all_files_before_mutation(tmp_path: Path) -> None:
    atomic_write(tmp_path, "one.txt", b"one")
    atomic_write(tmp_path, "two.txt", b"two")
    patch = PatchSet(
        base_snapshot=digest_for("candidate"),
        operations=[
            PatchOperation(operation="ModifyFile", path="one.txt", preimage_digest=content_digest(b"one"), content=b"ONE", postimage_digest=content_digest(b"ONE")),
            PatchOperation(operation="ModifyFile", path="two.txt", preimage_digest=content_digest(b"wrong"), content=b"TWO", postimage_digest=content_digest(b"TWO")),
        ],
    )
    with pytest.raises(ToolProtocolError, match="TOOL_STALE_PRECONDITION"):
        apply_patch_set(tmp_path, patch)
    assert (tmp_path / "one.txt").read_bytes() == b"one"
    assert (tmp_path / "two.txt").read_bytes() == b"two"


def test_patch_rename_is_preconditioned_and_atomic(tmp_path: Path) -> None:
    atomic_write(tmp_path, "old.txt", b"contents")
    patch = PatchSet(
        base_snapshot=digest_for("candidate"),
        operations=[PatchOperation(operation="RenameFile", from_path="old.txt", path="new.txt", preimage_digest=content_digest(b"contents"))],
    )
    assert apply_patch_set(tmp_path, patch) == ("old.txt", "new.txt")
    assert not (tmp_path / "old.txt").exists()
    assert (tmp_path / "new.txt").read_bytes() == b"contents"


def test_git_surface_excludes_network_and_sanitizes_hooks(tmp_path: Path) -> None:
    argv = build_git_argv("status", [], repo_root=tmp_path)
    assert "core.hooksPath=NUL" in argv
    with pytest.raises(ToolProtocolError):
        build_git_argv("push", [], repo_root=tmp_path)


def test_every_registered_schema_exists_and_contributes_to_digest() -> None:
    registry = load_tool_registry()
    assert all(tool_schema_digest(name).startswith("sha256:") for name in registry)


def test_process_exact_argv_stdin_timeout_and_secret_redaction(tmp_path: Path) -> None:
    result = execute_process(
        executable=sys.executable,
        argv=["-c", "import sys; print(sys.stdin.read()); print('token=secret')"],
        cwd=tmp_path,
        env={"PATH": str(Path(sys.executable).parent)},
        stdin=b"input",
        secret_values=("secret",),
    )
    assert result.status == "SUCCESS"
    assert "input" in result.stdout.text
    assert "secret" not in result.stdout.text


def test_process_timeout_is_not_success(tmp_path: Path) -> None:
    result = execute_process(
        executable=sys.executable,
        argv=["-c", "import time; time.sleep(2)"],
        cwd=tmp_path,
        env={"PATH": str(Path(sys.executable).parent)},
        timeout_ms=50,
    )
    assert result.status == "TIMEOUT"
    assert result.status != "SUCCESS"


def test_large_output_is_persisted_as_digest_addressed_artifact(tmp_path: Path) -> None:
    store = tmp_path / "artifacts"
    result = execute_process(
        executable=sys.executable,
        argv=["-c", "print('x' * 100)"],
        cwd=tmp_path,
        env={"PATH": str(Path(sys.executable).parent)},
        output_limit=8,
        artifact_store=store,
    )
    assert result.status == "SUCCESS"
    assert result.artifacts
    assert (store / result.artifacts[0].removeprefix("sha256:")).is_file()
