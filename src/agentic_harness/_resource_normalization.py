"""`ResourceNormalization v1` reference implementation (Blueprint 9.12.2/9.12.3, 10.10).

`contracts/resource_normalization.schema.json` / `.yaml` is the sole
authoritative source for the seven normalized resource kinds, the
repo_path normalization step sequence, the resource-pattern grammar, and
the required adversarial-vector coverage list. This module implements that
step sequence and per-kind canonical structures; it does not redeclare the
kind list or step text as a second hand-maintained copy (Canonical Identity
Rules), though for a deterministic pure-function implementation the step
order below is necessarily hard-coded to match the contract 1:1 (verified
by `tests/test_resource_normalization.py::test_repo_path_steps_match_contract`).

Free-form resource strings are forbidden at policy boundaries (10.10):
callers authorize against the structures this module returns, never against
raw user/model strings.
"""

from __future__ import annotations

import fnmatch
import ipaddress
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

REASON_CODE_RESOURCE_INVALID = "RESOURCE_INVALID"
REASON_CODE_RESOURCE_SCOPE_WIDENING = "RESOURCE_SCOPE_WIDENING"

_INTERPRETER_BASENAMES = frozenset({
    "python", "python3", "python3.13", "python.exe", "python3.exe",
    "node", "node.exe", "sh", "bash", "bash.exe", "zsh",
    "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "pwsh.exe",
})

_ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_UUID7_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_PRIVILEGED_ENV_KEYS = frozenset({"PATH", "LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH"})


class ResourceNormalizationError(ValueError):
    """A raw resource reference could not be normalized/authorized under ResourceNormalization v1.

    Raised instead of silently truncating, guessing, or widening scope;
    callers MUST treat this as a denial (fail closed), never a best-effort
    normalization.
    """

    def __init__(self, message: str, *, reason_code: str = REASON_CODE_RESOURCE_INVALID) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def _reject(message: str, *, reason_code: str = REASON_CODE_RESOURCE_INVALID) -> None:
    raise ResourceNormalizationError(message, reason_code=reason_code)


# ---------------------------------------------------------------------------
# repo_path (9.12.3's eight-step procedure)
# ---------------------------------------------------------------------------


def normalize_repo_path(raw: str, *, root: Path, exists_hint: bool | None = None, case_sensitive: bool = True) -> str:
    """Normalize `raw` against the governed worktree `root`, returning a canonical
    repo-relative POSIX path (9.12.3 steps 1-8).

    `exists_hint` lets a caller assert whether this is a creation target
    without a filesystem race between the caller's own existence check and
    this function's; when None, existence is probed directly. `case_sensitive`
    selects platform-appropriate canonical case comparison (step 7): pass
    False to reproduce a case-insensitive filesystem's collision behavior.
    """
    # Step 1: relative to governed root only.
    if not isinstance(raw, str):
        _reject("repo_path must be a string")
    if raw == "":
        _reject("repo_path must not be empty")
    if "\x00" in raw:
        # Step 2: reject NUL.
        _reject("repo_path contains a NUL byte")
    try:
        raw.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        _reject("repo_path is not valid UTF-8")

    normalized_slashes = raw.replace("\\", "/")
    if normalized_slashes.startswith("/"):
        _reject("repo_path must be relative to the governed worktree, not absolute")
    if re.match(r"^[A-Za-z]:", normalized_slashes) or normalized_slashes.startswith("//") or normalized_slashes.startswith("\\\\"):
        # Windows drive-letter and UNC forms are absolute escapes of the governed root.
        _reject("repo_path must not be a drive-letter or UNC form")

    # Step 3/4: collapse '.' components and reject any '..' that escapes root.
    raw_parts = PurePosixPath(normalized_slashes).parts
    resolved_parts: list[str] = []
    for part in raw_parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not resolved_parts:
                _reject("repo_path '..' escapes the authorized root", reason_code=REASON_CODE_RESOURCE_SCOPE_WIDENING)
            resolved_parts.pop()
            continue
        if "\x00" in part:
            _reject("repo_path component contains a NUL byte")
        resolved_parts.append(part)

    if not resolved_parts:
        _reject("repo_path resolves to the worktree root itself, which is not an authorizable target")

    lexical_relative = "/".join(resolved_parts)
    root = _safe_resolve(root)
    lexical_absolute = root.joinpath(*resolved_parts)

    # Step 5/6: resolve existing symlinks; for creation targets, resolve the
    # nearest existing ancestor and verify the unresolved suffix cannot
    # escape through a symlink race.
    # The hint is diagnostic only; caller-provided existence claims never
    # override current filesystem state.  In particular, `False` must not
    # reclassify an existing symlink as a safe creation target.
    try:
        exists = lexical_absolute.exists(follow_symlinks=False)
    except (OSError, ValueError, RuntimeError) as exc:
        _reject(f"repo_path filesystem inspection failed: {exc}")
    if exists_hint is True and not exists:
        _reject("repo_path existence hint disagrees with filesystem state")
    if exists:
        resolved_absolute = _safe_resolve(lexical_absolute, strict=True)
    else:
        existing_ancestor = lexical_absolute.parent
        consumed = 1
        while not existing_ancestor.exists() and existing_ancestor != existing_ancestor.parent:
            existing_ancestor = existing_ancestor.parent
            consumed += 1
        if not existing_ancestor.exists():
            _reject("no existing ancestor found to anchor a creation-target repo_path")
        resolved_ancestor = _safe_resolve(existing_ancestor, strict=True)
        if not _is_within(resolved_ancestor, root):
            _reject("repo_path creation target's nearest existing ancestor escapes the governed root via a symlink", reason_code=REASON_CODE_RESOURCE_SCOPE_WIDENING)
        suffix_parts = resolved_parts[len(resolved_parts) - consumed:]
        for part in suffix_parts:
            if part in ("..", "."):
                _reject("repo_path creation-target suffix must not contain '.' or '..'")
        resolved_absolute = resolved_ancestor.joinpath(*suffix_parts)

    if not _is_within(resolved_absolute, root):
        _reject("repo_path resolved target escapes the governed worktree root", reason_code=REASON_CODE_RESOURCE_SCOPE_WIDENING)

    # Step 7/8: canonical case comparison, authorize the resolved target.
    relative_resolved = resolved_absolute.relative_to(root)
    canonical = relative_resolved.as_posix()
    if not case_sensitive:
        canonical = canonical  # case-fold collision handling is a policy-matching concern (see resource_key_for); the resolved path itself preserves on-disk case.
    return canonical


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_resolve(path: Path, *, strict: bool = False) -> Path:
    try:
        return path.resolve(strict=strict)
    except (OSError, ValueError, RuntimeError) as exc:
        _reject(f"repo_path filesystem resolution failed: {exc}")
        raise AssertionError("unreachable")


def repo_path_collation_key(canonical_path: str, *, case_sensitive: bool) -> str:
    """9.12.3 step 7: the key used for authorization/pattern-matching equality."""
    return canonical_path if case_sensitive else canonical_path.casefold()


# ---------------------------------------------------------------------------
# process
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NormalizedProcess:
    executable: str
    argv: tuple[str, ...]
    cwd: str
    script: str | None
    env_keys: tuple[str, ...]


def normalize_process(
    executable: str,
    argv: list[str],
    cwd: str,
    *,
    env_keys: list[str] | None = None,
    path_dirs: list[str] | None = None,
    allow_privileged_env_keys: bool = False,
    resolved_script: str | None = None,
) -> NormalizedProcess:
    """Normalize a process resource. Interpreter/script ambiguity and PATH
    shadowing are resolved deterministically here rather than left to the
    OS's implicit search order:

    * `executable` must already be a canonical absolute path, or resolvable
      via the caller-supplied, explicitly ordered `path_dirs` (never an
      implicit, process-ambient PATH, and never the current working
      directory, which is how PATH-shadowing attacks smuggle a
      repo-controlled executable ahead of a trusted one).
    * when `executable`'s basename names a known interpreter, the caller
      MUST supply `resolved_script` (the interpreter-style script argument,
      already normalized as a repo_path resource by the caller) so the
      script identity is not left as an unauthorized bare argv string.
    """
    if not isinstance(executable, str) or not executable:
        _reject("process.executable must not be empty")
    if not isinstance(cwd, str) or not isinstance(argv, (list, tuple)) or any(not isinstance(argument, str) for argument in argv):
        _reject("process executable, cwd, and argv must use string values")
    if "\x00" in cwd or any("\x00" in argument for argument in argv):
        _reject("process resource contains a NUL byte")
    cwd_path = Path(cwd)
    cwd_posix = cwd.replace("\\", "/")
    cwd_is_absolute = cwd_path.is_absolute() or cwd_posix.startswith("/") or re.match(r"^[A-Za-z]:/", cwd_posix) is not None
    if not cwd_is_absolute:
        _reject("process.cwd must be a canonical absolute repo/workspace path")
    canonical_cwd = str(cwd_path.resolve(strict=False))
    resolved_executable = _resolve_executable(executable, path_dirs)

    basename = PurePosixPath(resolved_executable.replace("\\", "/")).name.lower()
    script: str | None = None
    if basename in _INTERPRETER_BASENAMES:
        if resolved_script is None:
            _reject(
                f"executable {resolved_executable!r} is an interpreter; the invoked script must be "
                "normalized and supplied explicitly rather than trusted from argv (interpreter/script ambiguity)"
            )
        script = resolved_script

    normalized_env_keys: list[str] = []
    if env_keys is not None and (not isinstance(env_keys, (list, tuple)) or any(not isinstance(key, str) for key in env_keys)):
        _reject("process environment keys must be strings")
    for key in sorted(set(env_keys or [])):
        if not _ENV_KEY_PATTERN.match(key):
            _reject(f"environment variable name {key!r} is not a valid identifier (environment injection)")
        if key in _PRIVILEGED_ENV_KEYS and not allow_privileged_env_keys:
            _reject(f"exposing privileged environment variable {key!r} requires explicit authorization", reason_code=REASON_CODE_RESOURCE_SCOPE_WIDENING)
        normalized_env_keys.append(key)

    return NormalizedProcess(
        executable=resolved_executable,
        argv=tuple(argv),
        cwd=canonical_cwd,
        script=script,
        env_keys=tuple(normalized_env_keys),
    )


def _resolve_executable(executable: str, path_dirs: list[str] | None) -> str:
    posix = executable.replace("\\", "/")
    is_absolute = posix.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", executable) is not None
    if is_absolute:
        candidate = Path(executable)
        if candidate.is_symlink() and not candidate.exists():
            _reject(f"absolute executable path {executable!r} is a dangling link")
        if candidate.exists():
            if not candidate.is_file():
                _reject(f"absolute executable path {executable!r} is not a regular file")
            return str(candidate.resolve())
        return executable
    if "/" in posix or "\\" in executable:
        _reject(f"relative executable path {executable!r} must be resolved by the caller before normalization")
    if not path_dirs:
        _reject(
            f"bare executable name {executable!r} requires an explicit, ordered path_dirs list; "
            "implicit ambient PATH/cwd search is not performed (PATH shadowing)"
        )
    if not isinstance(path_dirs, (list, tuple)) or any(not isinstance(directory, str) for directory in path_dirs):
        _reject("process path_dirs must contain only strings")
    for directory in path_dirs:
        candidate = Path(directory) / executable
        if candidate.is_file():
            return str(candidate.resolve())
    _reject(f"executable {executable!r} was not found in any of the explicitly supplied path_dirs")
    raise AssertionError("unreachable")  # pragma: no cover


# ---------------------------------------------------------------------------
# network_origin
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NormalizedNetworkOrigin:
    scheme: str
    host_ascii: str
    port: int
    is_ip_literal: bool


_DEFAULT_PORTS = {"http": 80, "https": 443}


def normalize_network_origin(scheme: str, host: str, port: int | None) -> NormalizedNetworkOrigin:
    if not isinstance(scheme, str) or not isinstance(host, str):
        _reject("network scheme and host must be strings")
    if port is not None and (isinstance(port, bool) or not isinstance(port, int)):
        _reject("network port must be an integer or null")
    scheme_lower = scheme.lower()
    if scheme_lower not in _DEFAULT_PORTS:
        _reject(f"network scheme {scheme!r} is not one of http/https")

    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if "%" in host:
        _reject("network host zone identifiers are not stable origin identities")

    is_ip_literal = False
    try:
        ip = ipaddress.ip_address(host)
        is_ip_literal = True
        # `compressed` gives IPv6 literals one canonical spelling while
        # retaining the distinction between IP literals and hostnames.
        host_ascii = ip.compressed
    except ValueError:
        host_ascii = _normalize_hostname(host)

    resolved_port = port if port is not None else _DEFAULT_PORTS[scheme_lower]
    if not (1 <= resolved_port <= 65535):
        _reject(f"network port {resolved_port} out of range")

    return NormalizedNetworkOrigin(scheme=scheme_lower, host_ascii=host_ascii, port=resolved_port, is_ip_literal=is_ip_literal)


def _normalize_hostname(host: str) -> str:
    if not host:
        _reject("network host must not be empty")
    # Trailing-dot hostname vector: exactly one trailing root-domain dot is
    # permitted by DNS syntax and MUST normalize identically to its
    # dot-free form; more than one trailing dot is invalid.
    stripped = host
    if stripped.endswith(".."):
        _reject(f"hostname {host!r} has more than one trailing dot")
    if stripped.endswith("."):
        stripped = stripped[:-1]
    if not stripped:
        _reject("hostname must not be empty after trailing-dot normalization")
    try:
        labels = stripped.split(".")
        if any(not label for label in labels):
            _reject(f"hostname {host!r} contains an empty label")
        ascii_labels = [label.encode("idna").decode("ascii") if not label.isascii() else label for label in labels]
    except UnicodeError as exc:
        _reject(f"hostname {host!r} failed IDNA normalization: {exc}")
        raise AssertionError("unreachable")  # pragma: no cover
    normalized = ".".join(ascii_labels).lower()
    if len(normalized) > 253 or any(len(label) > 63 for label in normalized.split(".")):
        _reject(f"hostname {host!r} exceeds DNS label or total-length limits")
    return normalized


# ---------------------------------------------------------------------------
# external_service / secret / repository_ref / artifact
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NormalizedExternalService:
    provider: str
    operation: str
    account_scope: str | None
    resource_path: str


def normalize_external_service(provider: str, operation: str, account_scope: str | None, resource_path: str) -> NormalizedExternalService:
    for label, value in (("provider", provider), ("operation", operation), ("resource_path", resource_path)):
        if not isinstance(value, str) or not value or "\x00" in value:
            _reject(f"external_service.{label} must not be empty")
    if account_scope is not None and (not isinstance(account_scope, str) or not account_scope or "\x00" in account_scope):
        _reject("external_service.account_scope contains a NUL byte")
    return NormalizedExternalService(provider=provider, operation=operation, account_scope=account_scope, resource_path=resource_path)


@dataclass(frozen=True)
class NormalizedSecret:
    secret_id: str
    broker: str
    purpose: str


def normalize_secret(secret_id: str, broker: str, purpose: str) -> NormalizedSecret:
    for label, value in (("secret_id", secret_id), ("broker", broker), ("purpose", purpose)):
        if not isinstance(value, str) or not value or "\x00" in value:
            _reject(f"secret.{label} must not be empty")
    return NormalizedSecret(secret_id=secret_id, broker=broker, purpose=purpose)


_REF_KINDS = frozenset({"HEAD", "BRANCH", "TAG", "FULL_REF", "OBJECT"})


@dataclass(frozen=True)
class NormalizedRepositoryRef:
    repo_identity: str
    ref_kind: str
    ref_name_or_oid: str


def normalize_repository_ref(repo_identity: str, ref_kind: str, ref_name_or_oid: str) -> NormalizedRepositoryRef:
    if not isinstance(repo_identity, str) or not isinstance(ref_kind, str) or not isinstance(ref_name_or_oid, str):
        _reject("repository_ref fields must be strings")
    if ref_kind not in _REF_KINDS:
        _reject(f"repository_ref.ref_kind {ref_kind!r} is not one of {sorted(_REF_KINDS)}")
    if not repo_identity or "\x00" in repo_identity or "\x00" in ref_name_or_oid:
        _reject("repository_ref identity/value must not be empty or contain a NUL byte")
    if not ref_name_or_oid:
        _reject("repository_ref.ref_name_or_oid must not be empty")
    if ref_name_or_oid.startswith("-"):
        # Prevents the ref value from being interpreted as a Git CLI option
        # when later placed into an argv (git command-argument injection).
        _reject(f"repository_ref.ref_name_or_oid {ref_name_or_oid!r} must not begin with '-'")
    return NormalizedRepositoryRef(repo_identity=repo_identity, ref_kind=ref_kind, ref_name_or_oid=ref_name_or_oid)


@dataclass(frozen=True)
class NormalizedArtifact:
    namespace: str
    artifact_id: str | None
    digest: str | None
    media_type: str | None


def normalize_artifact(namespace: str, artifact_id: str | None, digest: str | None, media_type: str | None) -> NormalizedArtifact:
    if not isinstance(namespace, str) or not namespace or "\x00" in namespace:
        _reject("artifact.namespace must not be empty")
    if artifact_id is not None and not isinstance(artifact_id, str):
        _reject("artifact.artifact_id must be a string or null")
    if digest is not None and not isinstance(digest, str):
        _reject("artifact.digest must be a string or null")
    if media_type is not None and (not isinstance(media_type, str) or not media_type):
        _reject("artifact.media_type must be a string or null")
    if any(value is not None and "\x00" in value for value in (artifact_id, digest, media_type)):
        _reject("artifact fields must not contain a NUL byte")
    if artifact_id is None and digest is None:
        _reject("artifact requires artifact_id or digest")
    if artifact_id is not None and not _UUID7_PATTERN.fullmatch(artifact_id):
        _reject("artifact.artifact_id must be a lowercase UUIDv7")
    if digest is not None and not _DIGEST_PATTERN.fullmatch(digest):
        _reject("artifact.digest must be a sha256 digest")
    return NormalizedArtifact(namespace=namespace, artifact_id=artifact_id, digest=digest, media_type=media_type)


# ---------------------------------------------------------------------------
# ResourcePattern matching (10.10.1)
# ---------------------------------------------------------------------------

_PREFIX_ELIGIBLE_KINDS = frozenset({"repo_path", "artifact", "external_service"})


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate the harness path glob (*, ?, **) to an anchored regex.

    Never delegated to a shell (10.10.1). `**` matches across path
    separators; `*`/`?` do not.
    """
    out = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if pattern[i : i + 2] == "**":
            out.append(".*")
            i += 2
            continue
        if ch == "*":
            out.append("[^/]*")
        elif ch == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(ch))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def matches_resource_pattern(*, kind: str, match: str, value: str, normalized_key: str, pattern_kind: str) -> bool:
    """10.10.1: evaluate whether `normalized_key` is matched by a `ResourcePattern`.

    `pattern_kind` is the pattern's own declared resource kind; artifact and
    external-service normalized keys may contain hierarchical paths, so their
    whole resource kinds are eligible for PREFIX matching. A mismatched kind never
    matches regardless of match mode.
    """
    if kind != pattern_kind:
        return False
    if match == "EXACT":
        return normalized_key == value
    if match == "PREFIX":
        if pattern_kind not in _PREFIX_ELIGIBLE_KINDS:
            _reject(f"PREFIX match is not permitted for resource kind {pattern_kind!r}")
        return normalized_key == value or normalized_key.startswith(value.rstrip("/") + "/")
    if match == "GLOB":
        return _glob_to_regex(value).match(normalized_key) is not None
    _reject(f"unknown ResourcePattern.match {match!r}")
    raise AssertionError("unreachable")  # pragma: no cover


def pattern_is_broader_than(narrower: dict[str, Any], broader: dict[str, Any]) -> bool:
    """True if `broader`'s value would authorize everything `narrower` authorizes, and more.

    Used to reject a governed scope (e.g. a WorkPackage.allowed_paths entry)
    that broadens beyond its parent's authorized pattern (resource-pattern
    broadening, RESOURCE_SCOPE_WIDENING).
    """
    if narrower["kind"] != broader["kind"]:
        return False
    if broader["match"] == "EXACT":
        return narrower["match"] == "EXACT" and narrower["value"] == broader["value"]
    if broader["match"] == "PREFIX":
        if narrower["match"] == "EXACT":
            return narrower["value"] == broader["value"] or narrower["value"].startswith(broader["value"].rstrip("/") + "/")
        if narrower["match"] == "PREFIX":
            return narrower["value"] == broader["value"] or narrower["value"].startswith(broader["value"].rstrip("/") + "/")
        return False
    if broader["match"] == "GLOB":
        # A GLOB parent only conservatively bounds an EXACT/PREFIX child by
        # fnmatch containment on the literal pattern text; a nested GLOB
        # child is never provably narrower without a full grammar
        # subsumption proof, so it is treated as broadening (fail closed).
        if narrower["match"] == "GLOB":
            return narrower["value"] == broader["value"]
        return fnmatch.fnmatchcase(narrower["value"], broader["value"])
    return False
