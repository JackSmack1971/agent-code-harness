from pathlib import Path

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


def test_git_surface_excludes_network_and_sanitizes_hooks(tmp_path: Path) -> None:
    argv = build_git_argv("status", [], repo_root=tmp_path)
    assert "core.hooksPath=NUL" in argv
    with pytest.raises(ToolProtocolError):
        build_git_argv("push", [], repo_root=tmp_path)
