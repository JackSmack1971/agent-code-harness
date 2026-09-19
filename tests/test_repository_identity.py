from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from agentic_harness._repository_identity import (
    RepositoryIdentityError,
    WorkspaceOverlay,
    capture_repository_snapshot,
    choose_dirty_state,
)


def git(root: Path, *args: str, check: bool = True) -> bytes:
    return subprocess.run(["git", *args], cwd=root, check=check, capture_output=True).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "tracked.txt").write_bytes(b"base\n")
    git(tmp_path, "add", "tracked.txt")
    git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def test_clean_snapshot_is_deterministic_and_tagged(repo: Path) -> None:
    first = capture_repository_snapshot(repo)
    second = capture_repository_snapshot(repo)
    assert first.digest == second.digest
    assert first.head_commit and first.head_commit.startswith("sha1:")
    assert first.index_entries[0].object_oid.startswith("sha1:")
    assert first.sparse_checkout.enabled is False
    assert first.is_dirty is False


def test_staged_and_worktree_bytes_are_distinct(repo: Path) -> None:
    base = capture_repository_snapshot(repo)
    (repo / "tracked.txt").write_bytes(b"staged\n")
    git(repo, "add", "tracked.txt")
    staged = capture_repository_snapshot(repo)
    (repo / "tracked.txt").write_bytes(b"worktree\n")
    partial = capture_repository_snapshot(repo)
    assert staged.index_digest != base.index_digest
    assert partial.index_digest == staged.index_digest
    assert partial.tracked_worktree_digest != staged.tracked_worktree_digest
    assert choose_dirty_state(partial, capture=True) == "CAPTURE_DIRTY_STATE"
    with pytest.raises(RepositoryIdentityError):
        choose_dirty_state(partial)


def test_untracked_is_exact_and_ignored_is_excluded(repo: Path) -> None:
    (repo / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (repo / "ignored.txt").write_bytes(b"ignored")
    (repo / "new.txt").write_bytes(b"new")
    snapshot = capture_repository_snapshot(repo)
    paths = [e.path_bytes for e in snapshot.untracked_entries]
    assert b"new.txt" in paths and b"ignored.txt" not in paths
    assert snapshot.is_dirty is True


def test_symlink_and_executable_mode_are_identity_bearing(repo: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("platform has no symlink support")
    (repo / "exec.sh").write_bytes(b"#!/bin/sh\n")
    os.chmod(repo / "exec.sh", 0o755)
    try:
        os.symlink("tracked.txt", repo / "link")
    except OSError as exc:
        pytest.skip(f"symlink privilege unavailable: {exc}")
    git(repo, "add", "exec.sh", "link")
    snapshot = capture_repository_snapshot(repo)
    entries = {e.path_bytes: e for e in snapshot.tracked_entries}
    assert entries[b"exec.sh"].mode == "100755"
    assert entries[b"link"].entry_type == "symlink"


def test_unborn_head_and_detached_head(repo: Path) -> None:
    empty = repo.parent / "empty"
    empty.mkdir()
    git(empty, "init", "-q")
    unborn = capture_repository_snapshot(empty)
    assert unborn.head_commit is None and unborn.head_ref == "refs/heads/master"
    git(repo, "checkout", "--detach", "-q")
    detached = capture_repository_snapshot(repo)
    assert detached.head_ref is None and detached.head_commit is not None


def test_overlay_captures_exact_bytes(repo: Path) -> None:
    (repo / "tracked.txt").write_bytes(b"dirty\x00bytes")
    (repo / "new.bin").write_bytes(b"\x00\xff")
    snapshot = capture_repository_snapshot(repo)
    overlay = WorkspaceOverlay.capture(snapshot)
    assert dict(overlay.tracked_bytes)[b"tracked.txt"] == b"dirty\x00bytes"
    assert dict(overlay.untracked_bytes)[b"new.bin"] == b"\x00\xff"
    assert overlay.record()["source_snapshot"] == snapshot.digest


def test_overlay_replay_reconstructs_snapshot_components(repo: Path) -> None:
    base = capture_repository_snapshot(repo)
    (repo / "tracked.txt").write_bytes(b"staged exact")
    git(repo, "add", "tracked.txt")
    (repo / "untracked.bin").write_bytes(b"\x00exact")
    source = capture_repository_snapshot(repo)
    overlay = WorkspaceOverlay.capture(source)
    target = repo.parent / "replay-target"
    subprocess.run(["git", "clone", "-q", str(repo), str(target)], check=True, capture_output=True)
    overlay.replay(target, base_commit=base.head_commit.split(":", 1)[1] if base.head_commit else None)
    replayed = capture_repository_snapshot(target)
    assert replayed.index_digest == source.index_digest
    assert replayed.tracked_worktree_digest == source.tracked_worktree_digest
    assert replayed.untracked_manifest_digest == source.untracked_manifest_digest


def test_rename_deleted_and_intent_to_add_are_state_based(repo: Path) -> None:
    git(repo, "mv", "tracked.txt", "renamed.txt")
    (repo / "planned.txt").write_bytes(b"planned")
    git(repo, "add", "-N", "planned.txt")
    git(repo, "rm", "--cached", "renamed.txt")
    snapshot = capture_repository_snapshot(repo)
    paths = {entry.path_bytes for entry in snapshot.index_entries}
    assert b"renamed.txt" not in paths
    assert b"planned.txt" in paths
    assert next(e for e in snapshot.index_entries if e.path_bytes == b"planned.txt").intent_to_add


def test_merge_conflict_preserves_all_index_stages(repo: Path) -> None:
    git(repo, "checkout", "-qb", "side")
    (repo / "tracked.txt").write_bytes(b"side\n")
    git(repo, "commit", "-qam", "side")
    git(repo, "checkout", "-q", "master")
    (repo / "tracked.txt").write_bytes(b"main\n")
    git(repo, "commit", "-qam", "main")
    git(repo, "merge", "side", check=False)
    snapshot = capture_repository_snapshot(repo)
    stages = [e.stage for e in snapshot.index_entries if e.path_bytes == b"tracked.txt"]
    assert stages == [1, 2, 3]


def test_sparse_checkout_identity_binds_mode_and_patterns(repo: Path) -> None:
    (repo / "keep.txt").write_bytes(b"keep")
    (repo / "omit.txt").write_bytes(b"omit")
    git(repo, "add", "keep.txt", "omit.txt")
    git(repo, "commit", "-qm", "files")
    git(repo, "sparse-checkout", "init", "--no-cone")
    git(repo, "sparse-checkout", "set", "keep.txt")
    snapshot = capture_repository_snapshot(repo)
    assert snapshot.sparse_checkout.enabled is True
    assert snapshot.sparse_checkout.cone is False
    assert snapshot.sparse_checkout.patterns_digest is not None


def test_submodule_manifest_binds_gitlink_and_nested_dirty_state(repo: Path) -> None:
    nested = repo.parent / "nested-source"
    nested.mkdir()
    git(nested, "init", "-q")
    git(nested, "config", "user.email", "test@example.invalid")
    git(nested, "config", "user.name", "Test")
    (nested / "file").write_text("one", encoding="utf-8")
    git(nested, "add", "file")
    git(nested, "commit", "-qm", "nested")
    subprocess.run(["git", "-c", "protocol.file.allow=always", "submodule", "add", str(nested), "sub"], cwd=repo, check=True, capture_output=True)
    git(repo, "commit", "-qm", "submodule")
    clean = capture_repository_snapshot(repo)
    (repo / "sub" / "file").write_text("two", encoding="utf-8")
    dirty = capture_repository_snapshot(repo)
    assert dirty.submodule_manifest_digest != clean.submodule_manifest_digest


def test_non_utf8_path_uses_explicit_encoding_or_fails_closed(repo: Path) -> None:
    if os.name == "nt":
        pytest.skip("Windows cannot materialize non-UTF-8 filenames")
    path = os.fsdecode(b"non-utf8-\xff")
    (repo / path).write_bytes(b"bytes")
    git(repo, "add", "--", path)
    snapshot = capture_repository_snapshot(repo)
    encoded = next(e for e in snapshot.index_entries if e.path_bytes.startswith(b"non-utf8-"))
    assert encoded.record()["path_bytes"]["encoding"] == "base64url"


def test_case_collision_is_rejected_on_case_insensitive_platform(repo: Path) -> None:
    (repo / "Case").write_bytes(b"a")
    (repo / "case").write_bytes(b"b")
    if os.path.samefile(repo / "Case", repo / "case"):
        pytest.skip("case-colliding names cannot coexist in this worktree")
    git(repo, "add", "--", "Case", "case")
    if os.path.normcase("A") == os.path.normcase("a"):
        from agentic_harness._repository_identity import RepositoryUnsupportedState
        with pytest.raises(RepositoryUnsupportedState):
            capture_repository_snapshot(repo)
    else:
        snapshot = capture_repository_snapshot(repo)
        assert {e.path_bytes for e in snapshot.index_entries} >= {b"Case", b"case"}


def test_required_golden_fixture_inventory(repo_root: Path) -> None:
    fixture = json.loads((repo_root / "contracts/tests/repository_identity/golden.json").read_text())
    names = {item["name"] for item in fixture["fixtures"]}
    assert names == {
        "clean", "modified", "staged", "partially_staged", "untracked", "ignored", "symlink",
        "executable_bit", "rename", "deleted_staged", "intent_to_add", "merge_conflict",
        "submodule_clean", "submodule_dirty", "detached_head", "unborn_branch", "sparse_checkout",
        "non_utf8_path", "case_collision_manifest",
    }
