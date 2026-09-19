from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

FIXTURES_DIR_NAME = "domain_schemas"


def _schema_doc(contracts_root: Path) -> dict[str, Any]:
    return json.loads((contracts_root / "domain_schemas.schema.json").read_text(encoding="utf-8"))


def _semantic_types_doc(contracts_root: Path) -> dict[str, Any]:
    return json.loads((contracts_root / "semantic_types.schema.json").read_text(encoding="utf-8"))


def _state_machine_doc(contracts_root: Path) -> dict[str, Any]:
    return json.loads((contracts_root / "state_machine.schema.json").read_text(encoding="utf-8"))


def _registry(contracts_root: Path) -> tuple[Registry, dict[str, Any]]:
    dom = _schema_doc(contracts_root)
    sem = _semantic_types_doc(contracts_root)
    sm = _state_machine_doc(contracts_root)
    registry = Registry().with_resources(
        [
            (sem["$id"], Resource.from_contents(sem)),
            (sm["$id"], Resource.from_contents(sm)),
            (dom["$id"], Resource.from_contents(dom)),
        ]
    )
    return registry, dom


def _validator_for(defname: str, contracts_root: Path) -> Draft202012Validator:
    registry, dom = _registry(contracts_root)
    return Draft202012Validator({"$ref": f"{dom['$id']}#/$defs/{defname}"}, registry=registry)


def _load_fixture(contracts_root: Path, name: str) -> list[dict[str, Any]]:
    path = contracts_root / "tests" / FIXTURES_DIR_NAME / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_document_is_valid_draft_2020_12(contracts_root: Path) -> None:
    Draft202012Validator.check_schema(_schema_doc(contracts_root))


def test_golden_fixtures_directory_exists(contracts_root: Path) -> None:
    golden = contracts_root / "tests" / FIXTURES_DIR_NAME / "golden.json"
    adversarial = contracts_root / "tests" / FIXTURES_DIR_NAME / "adversarial.json"
    assert golden.is_file()
    assert adversarial.is_file()


def _golden_cases(contracts_root: Path) -> list[tuple[str, Any]]:
    return [(c["def"], c["value"]) for c in _load_fixture(contracts_root, "golden.json")]


def _adversarial_cases(contracts_root: Path) -> list[tuple[str, Any]]:
    return [(c["def"], c["value"]) for c in _load_fixture(contracts_root, "adversarial.json")]


@pytest.mark.parametrize(
    "defname,value",
    _golden_cases(Path(__file__).resolve().parents[1] / "contracts"),
)
def test_golden_domain_schema_values_validate(defname: str, value: Any, contracts_root: Path) -> None:
    validator = _validator_for(defname, contracts_root)
    errors = sorted(validator.iter_errors(value), key=str)
    assert not errors, f"{defname}: {[e.message for e in errors]}"


@pytest.mark.parametrize(
    "defname,value",
    _adversarial_cases(Path(__file__).resolve().parents[1] / "contracts"),
)
def test_adversarial_domain_schema_values_are_rejected(defname: str, value: Any, contracts_root: Path) -> None:
    validator = _validator_for(defname, contracts_root)
    assert not validator.is_valid(value), f"{defname}: {value!r} unexpectedly validated"


def test_top_level_schema_carries_required_contract_metadata(contracts_root: Path) -> None:
    doc = _schema_doc(contracts_root)
    assert doc["x-contract-name"] == "DomainSchemas"
    assert doc["x-contract-version"] == 1


def test_every_defs_entry_is_documented_or_is_a_direct_ref(contracts_root: Path) -> None:
    doc = _schema_doc(contracts_root)
    for name, definition in doc["$defs"].items():
        is_documented = "description" in definition or "$comment" in definition
        is_ref_alias = set(definition.keys()) <= {"$ref", "description", "$comment"}
        assert is_documented or is_ref_alias, f"$defs/{name} carries neither description/$comment nor is a simple $ref alias"


def test_every_registered_schema_has_golden_and_is_additionalproperties_false(contracts_root: Path) -> None:
    doc = _schema_doc(contracts_root)
    registered = set(doc["x-registered-schemas"])
    golden_defs = {c["def"] for c in _load_fixture(contracts_root, "golden.json")}
    assert registered == golden_defs, f"registry/golden mismatch: {registered ^ golden_defs}"
    for name in registered:
        definition = doc["$defs"][name]
        assert definition.get("additionalProperties") is False, f"{name} must reject unknown fields"
        assert "schema_name" in definition["required"]
        assert "schema_version" in definition["required"]


def test_only_approval_grant_omits_digest(contracts_root: Path) -> None:
    doc = _schema_doc(contracts_root)
    for name in doc["x-registered-schemas"]:
        definition = doc["$defs"][name]
        has_digest = "digest" in definition["properties"]
        if name == "ApprovalGrant":
            assert not has_digest, "ApprovalGrant intentionally has no digest field (9.6.3)"
        else:
            assert has_digest, f"{name} is missing a digest field required by the global identity rule (9.6.1)"
