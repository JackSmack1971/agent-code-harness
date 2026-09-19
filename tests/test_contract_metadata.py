from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

META_SCHEMA_NAME = "contract_meta.schema.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _all_schema_files(contracts_root: Path) -> list[Path]:
    return sorted(contracts_root.rglob("*.schema.json"))


def test_at_least_one_schema_file_exists(contracts_root: Path) -> None:
    assert _all_schema_files(contracts_root)


@pytest.mark.parametrize(
    "schema_path",
    _all_schema_files(Path(__file__).resolve().parents[1] / "contracts"),
    ids=lambda p: p.name,
)
def test_every_schema_is_valid_draft_2020_12(schema_path: Path) -> None:
    doc = _load(schema_path)
    Draft202012Validator.check_schema(doc)


@pytest.mark.parametrize(
    "schema_path",
    _all_schema_files(Path(__file__).resolve().parents[1] / "contracts"),
    ids=lambda p: p.name,
)
def test_every_schema_carries_required_metadata(schema_path: Path, contracts_root: Path) -> None:
    meta_schema = _load(contracts_root / "meta" / META_SCHEMA_NAME)
    doc = _load(schema_path)
    validator = Draft202012Validator(meta_schema)
    errors = sorted(validator.iter_errors(doc), key=str)
    assert not errors, f"{schema_path}: {[e.message for e in errors]}"

    assert doc["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert doc["$id"], "schema must declare a stable $id"
    assert isinstance(doc["x-contract-name"], str) and doc["x-contract-name"]
    assert isinstance(doc["x-contract-version"], int) and doc["x-contract-version"] >= 1

    if schema_path.name == META_SCHEMA_NAME:
        # Documented extension point: this schema validates other schema
        # documents and therefore does not fix additionalProperties.
        return
    assert doc.get("additionalProperties") is False, (
        f"{schema_path}: normative schemas MUST set additionalProperties:false "
        "unless an extension point is documented via $comment"
    )


def test_schema_ids_are_unique(contracts_root: Path) -> None:
    ids = [_load(p)["$id"] for p in _all_schema_files(contracts_root)]
    assert len(ids) == len(set(ids)), "duplicate $id across contract schemas"


def test_contract_names_are_unique(contracts_root: Path) -> None:
    names = [_load(p)["x-contract-name"] for p in _all_schema_files(contracts_root)]
    assert len(names) == len(set(names)), "duplicate x-contract-name across contract schemas"
