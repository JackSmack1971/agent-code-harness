from __future__ import annotations

from pathlib import Path

COMPETING_LOCK_ARTIFACTS = [
    "poetry.lock",
    "Pipfile.lock",
    "Pipfile",
    "requirements.txt",
    "requirements-dev.txt",
    "setup.py",
    "setup.cfg",
]


def test_uv_lock_is_the_only_committed_lock_authority(repo_root: Path) -> None:
    assert (repo_root / "uv.lock").is_file(), "uv.lock must be committed as the canonical lockfile"
    present = [name for name in COMPETING_LOCK_ARTIFACTS if (repo_root / name).is_file()]
    assert not present, f"competing dependency-resolution authorities present: {present}"


def test_pyproject_declares_single_build_backend(repo_root: Path) -> None:
    text = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'build-backend = "hatchling.build"' in text
    assert "[tool.poetry]" not in text
    assert "[tool.pdm]" not in text
