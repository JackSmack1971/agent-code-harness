from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml


def _registered_codes(contracts_root: Path) -> set[str]:
    registry = yaml.safe_load((contracts_root / "reason_code_registry.yaml").read_text(encoding="utf-8"))
    return {c["code"] for c in registry["codes"]}


def _load(contracts_root: Path, name: str) -> list[dict[str, Any]]:
    path = contracts_root / "tests" / "reason_codes" / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_fixture_files_exist(contracts_root: Path) -> None:
    assert (contracts_root / "tests" / "reason_codes" / "golden.json").is_file()
    assert (contracts_root / "tests" / "reason_codes" / "adversarial.json").is_file()


@pytest.mark.parametrize(
    "entry",
    _load(Path(__file__).resolve().parents[1] / "contracts", "golden.json"),
    ids=lambda e: str(e["reason_code"]),
)
def test_golden_reason_codes_are_registered(entry: dict[str, Any], contracts_root: Path) -> None:
    assert entry["reason_code"] in _registered_codes(contracts_root)


@pytest.mark.parametrize(
    "entry",
    _load(Path(__file__).resolve().parents[1] / "contracts", "adversarial.json"),
    ids=lambda e: repr(e["reason_code"]),
)
def test_adversarial_reason_codes_are_not_registered(entry: dict[str, Any], contracts_root: Path) -> None:
    assert entry["reason_code"] not in _registered_codes(contracts_root)
