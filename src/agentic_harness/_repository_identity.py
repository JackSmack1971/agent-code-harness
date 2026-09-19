"""RepositoryIdentity v1.

This module deliberately obtains repository facts from Git's byte-oriented
interfaces.  Display-decoded paths never participate in a digest.  All
durable digests use :mod:`agentic_harness._canonical`.
"""

from __future__ import annotations

import base64
import hashlib
import os
import stat
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ._canonical import digest_for


class RepositoryIdentityError(RuntimeError):
    """The repository cannot be represented without losing identity."""


class RepositoryUnsupportedState(RepositoryIdentityError):
    """The repository state is valid Git but unsupported on this platform."""


def _path_value(path_bytes: bytes) -> dict[str, str]:
    try:
        return {"encoding": "utf8", "value": path_bytes.decode("utf-8", "strict")}
    except UnicodeDecodeError:
        return {
            "encoding": "base64url",
            "value": base64.urlsafe_b64encode(path_bytes).decode("ascii").rstrip("="),
        }


def _digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _oid(value: bytes, algorithm: str) -> str | None:
    if not value or set(value) == {ord("0")}:  # unborn/intent-to-add object
        return None
    return f"{algorithm}:{value.decode('ascii')}"


def _mode(mode: int) -> str:
    return f"{stat.S_IFMT(mode) | stat.S_IMODE(mode):06o}"


def _run(root: Path, *args: str, check: bool = True) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=os.fspath(root), capture_output=True, check=check,
        )
    except FileNotFoundError as exc:
        raise RepositoryIdentityError("qualified system Git is unavailable") from exc
    if check:
        return completed.stdout
    return completed.stdout


def _git_path(root: Path, path: str) -> Path:
    raw = _run(root, "rev-parse", "--path-format=absolute", "--git-path", path).strip()
    return Path(os.fsdecode(raw))


@dataclass(frozen=True)
class IndexEntry:
    path_bytes: bytes
    stage: int
    mode: str
    object_oid: str | None
    intent_to_add: bool = False

    def record(self) -> dict[str, object]:
        flags = ["INTENT_TO_ADD"] if self.intent_to_add else []
        return {
            "path_bytes": _path_value(self.path_bytes), "stage": self.stage,
            "mode": self.mode, "object_oid": self.object_oid,
            "status_flags": flags,
        }


@dataclass(frozen=True)
class MaterializedEntry:
    path_bytes: bytes
    entry_type: str
    mode: str | None
    content_digest: str | None
    missing: bool = False

    def record(self) -> dict[str, object]:
        return {
            "path_bytes": _path_value(self.path_bytes), "entry_type": self.entry_type,
            "mode": self.mode, "content_digest": self.content_digest,
            "missing": self.missing,
        }


@dataclass(frozen=True)
class SparseCheckoutIdentity:
    enabled: bool
    cone: bool | None
    patterns_digest: str | None

    def record(self) -> dict[str, object]:
        return {"enabled": self.enabled, "cone": self.cone, "patterns_digest": self.patterns_digest}


@dataclass(frozen=True)
class RepositorySnapshot:
    repository_root_identity: str
    git_common_dir_identity: str
    object_algorithm: str
    head_commit: str | None
    head_ref: str | None
    index_digest: str
    tracked_worktree_digest: str
    untracked_manifest_digest: str
    submodule_manifest_digest: str
    sparse_checkout: SparseCheckoutIdentity
    is_dirty: bool
    digest: str
    index_entries: tuple[IndexEntry, ...] = ()
    tracked_entries: tuple[MaterializedEntry, ...] = ()
    untracked_entries: tuple[MaterializedEntry, ...] = ()

    def record(self) -> dict[str, object]:
        return {
            "repository_root_identity": self.repository_root_identity,
            "git_common_dir_identity": self.git_common_dir_identity,
            "object_algorithm": self.object_algorithm,
            "head_commit": self.head_commit, "head_ref": self.head_ref,
            "index_digest": self.index_digest,
            "tracked_worktree_digest": self.tracked_worktree_digest,
            "untracked_manifest_digest": self.untracked_manifest_digest,
            "submodule_manifest_digest": self.submodule_manifest_digest,
            "sparse_checkout": self.sparse_checkout.record(),
            "is_dirty": self.is_dirty,
        }

    def domain_record(self, captured_at: str) -> dict[str, object]:
        """Return the existing DomainSchemas-compatible RepositorySnapshot."""
        return {
            "schema_name": "RepositorySnapshot", "schema_version": 1,
            "repository_root_identity": self.repository_root_identity,
            "git_common_dir_identity": self.git_common_dir_identity,
            "head_commit": self.head_commit, "head_ref": self.head_ref,
            "index_digest": self.index_digest,
            "tracked_worktree_digest": self.tracked_worktree_digest,
            "untracked_manifest_digest": self.untracked_manifest_digest,
            "submodule_manifest_digest": self.submodule_manifest_digest,
            "is_dirty": self.is_dirty, "captured_at": captured_at,
            "digest": self.digest,
        }


def _index_entries(root: Path, algorithm: str) -> tuple[IndexEntry, ...]:
    raw = _run(root, "ls-files", "--stage", "-z")
    intent_paths: set[bytes] = set()
    for item in _run(root, "status", "--porcelain=v2", "-z", "--untracked-files=all").split(b"\0"):
        fields = item.split(b" ", 8)
        if len(fields) == 9 and fields[0] == b"1" and fields[1] == b".A":
            intent_paths.add(fields[8])
    entries: list[IndexEntry] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        header, path = item.split(b"\t", 1)
        mode, oid, stage = header.split(b" ")
        intent = path in intent_paths or (int(stage) == 0 and set(oid) == {ord("0")})
        entries.append(IndexEntry(path, int(stage), mode.decode("ascii"), _oid(oid, algorithm), intent))
    entries.sort(key=lambda e: (e.path_bytes, e.stage))
    return tuple(entries)


def _read_materialized(root: Path, path_bytes: bytes) -> MaterializedEntry:
    target = os.fsdecode(os.fsencode(root) + os.sep.encode() + path_bytes)
    try:
        info = os.lstat(target)
    except FileNotFoundError:
        return MaterializedEntry(path_bytes, "missing", None, None, True)
    if stat.S_ISLNK(info.st_mode):
        data = os.fsencode(os.readlink(target))
        return MaterializedEntry(path_bytes, "symlink", "120000", _digest_bytes(data))
    if stat.S_ISREG(info.st_mode):
        with open(target, "rb") as fh:
            data = fh.read()
        return MaterializedEntry(path_bytes, "file", "100755" if info.st_mode & stat.S_IXUSR else "100644", _digest_bytes(data))
    raise RepositoryUnsupportedState(f"tracked path has unsupported materialized type: {path_bytes!r}")


def _untracked_entries(root: Path) -> tuple[MaterializedEntry, ...]:
    raw = _run(root, "ls-files", "--others", "--exclude-standard", "-z")
    paths = sorted(p for p in raw.split(b"\0") if p)
    return tuple(_read_materialized(root, p) for p in paths)


def _manifest_digest(entries: Iterable[object]) -> str:
    return digest_for([e.record() for e in entries])


def _sparse(root: Path) -> SparseCheckoutIdentity:
    enabled_raw = _run(root, "config", "--get", "core.sparseCheckout", check=False).strip().lower()
    enabled = enabled_raw in {b"1", b"true", b"yes", b"on"}
    if not enabled:
        return SparseCheckoutIdentity(False, None, None)
    cone_raw = _run(root, "config", "--get", "core.sparseCheckoutCone", check=False).strip().lower()
    cone = cone_raw in {b"1", b"true", b"yes", b"on"}
    pattern_path = _git_path(root, "info/sparse-checkout")
    try:
        patterns = pattern_path.read_bytes()
    except FileNotFoundError as exc:
        raise RepositoryIdentityError("sparse checkout is enabled but its pattern file is absent") from exc
    canonical_patterns = [_path_value(line) for line in patterns.splitlines()]
    return SparseCheckoutIdentity(True, cone, digest_for(canonical_patterns))


def _submodules(root: Path, entries: tuple[IndexEntry, ...], algorithm: str) -> str:
    records: list[dict[str, object]] = []
    for entry in entries:
        if entry.mode != "160000":
            continue
        rel = os.fsdecode(entry.path_bytes)
        path = root / Path(rel.replace("/", os.sep))
        initialized = False
        nested_head: str | None = None
        dirty: bool | None = None
        if path.is_dir():
            probe = _run(path, "rev-parse", "--git-dir", check=False)
            initialized = bool(probe.strip())
            if initialized:
                nested_algo = _run(path, "rev-parse", "--show-object-format").strip().decode("ascii")
                nested = _run(path, "rev-parse", "-q", "--verify", "HEAD", check=False).strip()
                nested_head = _oid(nested, nested_algo)
                dirty = bool(_run(path, "status", "--porcelain=v1", "--untracked-files=all"))
        records.append({"path_bytes": _path_value(entry.path_bytes), "recorded_gitlink_oid": entry.object_oid,
                        "initialized": initialized, "nested_head": nested_head, "nested_dirty": dirty})
    return digest_for(records)


def capture_repository_snapshot(repo_root: str | os.PathLike[str] = ".") -> RepositorySnapshot:
    """Capture exact committed/index/worktree/untracked repository identity."""
    root = Path(repo_root).resolve()
    if _run(root, "rev-parse", "--is-inside-work-tree").strip() != b"true":
        raise RepositoryIdentityError("repository identity requires a non-bare worktree")
    algorithm = _run(root, "rev-parse", "--show-object-format").strip().decode("ascii")
    if algorithm not in {"sha1", "sha256"}:
        raise RepositoryUnsupportedState(f"unsupported Git object format: {algorithm}")
    common = Path(os.fsdecode(_run(root, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())).resolve()
    ref_raw = _run(root, "symbolic-ref", "-q", "HEAD", check=False).strip()
    head_ref = ref_raw.decode("utf-8", "strict") if ref_raw else None
    head_raw = _run(root, "rev-parse", "-q", "--verify", "HEAD", check=False).strip()
    head = _oid(head_raw, algorithm)
    index = _index_entries(root, algorithm)
    tracked_paths = tuple(e.path_bytes for e in index if e.stage == 0)
    tracked = tuple(_read_materialized(root, p) for p in sorted(tracked_paths))
    untracked = _untracked_entries(root)
    all_paths = [e.path_bytes for e in tracked] + [e.path_bytes for e in untracked]
    if os.path.normcase("A") == os.path.normcase("a"):
        folded = [os.fsdecode(p).casefold() for p in all_paths]
        if len(folded) != len(set(folded)):
            raise RepositoryUnsupportedState("case-colliding paths cannot be materialized distinctly on this platform")
    if os.name == "nt" and any("\udc80" <= ch <= "udcff" for p in all_paths for ch in os.fsdecode(p)):
        raise RepositoryUnsupportedState("non-UTF-8 Git paths are unsupported on Windows")
    sparse = _sparse(root)
    index_digest = _manifest_digest(index)
    tracked_digest = _manifest_digest(tracked)
    untracked_digest = _manifest_digest(untracked)
    submodule_digest = _submodules(root, index, algorithm)
    semantic = {
        "repository_format": {"object_algorithm": algorithm},
        "repository_root_identity": str(root), "git_common_dir_identity": str(common),
        "head_commit": head, "head_ref": head_ref, "index_digest": index_digest,
        "tracked_worktree_digest": tracked_digest, "untracked_manifest_digest": untracked_digest,
        "submodule_manifest_digest": submodule_digest, "sparse_checkout": sparse.record(),
    }
    digest = digest_for(semantic)
    dirty = bool(_run(root, "status", "--porcelain=v1", "--untracked-files=all"))
    return RepositorySnapshot(str(root), str(common), algorithm, head, head_ref, index_digest,
                              tracked_digest, untracked_digest, submodule_digest, sparse, dirty,
                              digest, index, tracked, untracked)


def choose_dirty_state(snapshot: RepositorySnapshot, *, capture: bool = False, block: bool = False) -> str:
    """Apply the explicit dirty-state choice; no dirty input is silently dropped."""
    if not snapshot.is_dirty:
        return "CLEAN_BASE"
    if capture and block:
        raise ValueError("CAPTURE_DIRTY_STATE and BLOCK_DIRTY_STATE are mutually exclusive")
    if capture:
        return "CAPTURE_DIRTY_STATE"
    if block:
        return "BLOCK_DIRTY_STATE"
    raise RepositoryIdentityError("dirty repository requires CLEAN_BASE, CAPTURE_DIRTY_STATE, or BLOCK_DIRTY_STATE")


@dataclass(frozen=True)
class WorkspaceOverlay:
    """Exact byte overlay sufficient for a later isolated-worktree replay."""

    source_snapshot: str
    index_entries: tuple[IndexEntry, ...]
    tracked_bytes: tuple[tuple[bytes, bytes | None], ...]
    untracked_bytes: tuple[tuple[bytes, bytes], ...]

    @classmethod
    def capture(cls, snapshot: RepositorySnapshot) -> WorkspaceOverlay:
        root = Path(snapshot.repository_root_identity)
        tracked: list[tuple[bytes, bytes | None]] = []
        for entry in snapshot.tracked_entries:
            path = os.fsdecode(os.fsencode(root) + os.sep.encode() + entry.path_bytes)
            if entry.missing:
                tracked.append((entry.path_bytes, None))
            elif entry.entry_type == "symlink":
                tracked.append((entry.path_bytes, os.fsencode(os.readlink(path))))
            else:
                tracked.append((entry.path_bytes, Path(path).read_bytes()))
        untracked: list[tuple[bytes, bytes]] = []
        for entry in snapshot.untracked_entries:
            path = os.fsdecode(os.fsencode(root) + os.sep.encode() + entry.path_bytes)
            if entry.entry_type == "symlink":
                data = os.fsencode(os.readlink(path))
            else:
                data = Path(path).read_bytes()
            untracked.append((entry.path_bytes, data))
        return cls(snapshot.digest, snapshot.index_entries, tuple(tracked), tuple(untracked))

    def record(self) -> dict[str, object]:
        encode = lambda data: None if data is None else base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")
        return {"source_snapshot": self.source_snapshot,
                "index_entries": [e.record() for e in self.index_entries],
                "tracked_bytes": [{"path_bytes": _path_value(p), "base64url": encode(b)} for p, b in self.tracked_bytes],
                "untracked_bytes": [{"path_bytes": _path_value(p), "base64url": encode(b)} for p, b in self.untracked_bytes]}

    def replay(self, target_root: str | os.PathLike[str], *, base_commit: str | None) -> None:
        """Replay exact bytes and index stages into an already-created base worktree.

        The caller must create ``target_root`` from the committed base first.
        This method refuses to turn an unborn source into an implicitly chosen
        base; the caller must pass ``None`` explicitly in that case.
        """
        target = Path(target_root).resolve()
        if base_commit:
            _run(target, "read-tree", "-u", base_commit)
        for path_bytes, data in self.tracked_bytes + self.untracked_bytes:
            target_path = os.fsdecode(os.fsencode(target) + os.sep.encode() + path_bytes)
            if data is None:
                try:
                    os.unlink(target_path)
                except FileNotFoundError:
                    pass
                continue
            Path(target_path).parent.mkdir(parents=True, exist_ok=True)
            # Symlink payloads are represented separately by the source
            # manifest; ordinary overlay bytes are regular-file content.
            Path(target_path).write_bytes(data)
        if self.index_entries:
            lines = []
            for entry in self.index_entries:
                oid = entry.object_oid.split(":", 1)[1] if entry.object_oid else "0" * 40
                lines.append(f"{entry.mode} {oid} {entry.stage}\t".encode("ascii") + entry.path_bytes + b"\n")
            subprocess.run(["git", "update-index", "--index-info"], cwd=target, input=b"".join(lines), check=True)


class RepositoryIdentity:
    """Namespace for the RepositoryIdentity v1 capture boundary."""

    @staticmethod
    def capture(repo_root: str | os.PathLike[str] = ".") -> RepositorySnapshot:
        return capture_repository_snapshot(repo_root)
