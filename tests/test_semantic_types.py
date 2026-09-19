from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.validators import RefResolver

from agentic_harness._semantic_validation import EvidenceRequirementError, validate_evidence_requirement

FIXTURES_DIR_NAME = "semantic_types"


def _schema_doc(contracts_root: Path) -> dict[str, Any]:
    return json.loads((contracts_root / "semantic_types.schema.json").read_text(encoding="utf-8"))


def _validator_for(defname: str, contracts_root: Path) -> Draft202012Validator:
    doc = _schema_doc(contracts_root)
    resolver = RefResolver.from_schema(doc)
    return Draft202012Validator({"$ref": f"#/$defs/{defname}"}, resolver=resolver)


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
def test_golden_semantic_type_values_validate(defname: str, value: Any, contracts_root: Path) -> None:
    validator = _validator_for(defname, contracts_root)
    errors = sorted(validator.iter_errors(value), key=str)
    assert not errors, f"{defname}: {[e.message for e in errors]}"


@pytest.mark.parametrize(
    "defname,value",
    _adversarial_cases(Path(__file__).resolve().parents[1] / "contracts"),
)
def test_adversarial_semantic_type_values_are_rejected(defname: str, value: Any, contracts_root: Path) -> None:
    validator = _validator_for(defname, contracts_root)
    assert not validator.is_valid(value), f"{defname}: {value!r} unexpectedly validated"


def test_every_defs_entry_is_documented_or_is_a_direct_ref(contracts_root: Path) -> None:
    doc = _schema_doc(contracts_root)
    for name, definition in doc["$defs"].items():
        is_documented = "description" in definition or "$comment" in definition
        is_ref_alias = set(definition.keys()) <= {"$ref", "$comment"}
        assert is_documented or is_ref_alias, f"$defs/{name} carries neither description/$comment nor is a simple $ref alias"


def test_top_level_schema_carries_required_contract_metadata(contracts_root: Path) -> None:
    doc = _schema_doc(contracts_root)
    assert doc["x-contract-name"] == "SemanticTypes"
    assert doc["x-contract-version"] == 1


def test_data_classification_order_is_the_single_authoritative_ordering(contracts_root: Path) -> None:
    doc = _schema_doc(contracts_root)
    order = doc["$defs"]["DataClassificationOrder"]["const"]
    assert order == ["PUBLIC", "INTERNAL", "SENSITIVE", "SECRET"]
    enum_values = set(doc["$defs"]["DataClassification"]["enum"])
    assert enum_values == set(order)


def test_taint_is_a_closed_independent_set(contracts_root: Path) -> None:
    doc = _schema_doc(contracts_root)
    assert set(doc["$defs"]["Taint"]["enum"]) == {
        "SECRET_DERIVED",
        "USER_PRIVATE",
        "REPOSITORY_UNTRUSTED",
        "EXTERNAL_UNTRUSTED",
        "MODEL_GENERATED",
        "TOOL_OUTPUT_UNTRUSTED",
    }


# ---------------------------------------------------------------------------
# EvidenceRequirement cross-field invariant (10.3.4), which plain JSON
# Schema cannot express: THRESHOLD requires 1 <= threshold <= len(claim_refs).
# ---------------------------------------------------------------------------


def test_threshold_within_bounds_is_accepted() -> None:
    validate_evidence_requirement("THRESHOLD", ["a", "b", "c"], 2)


def test_threshold_of_zero_is_rejected() -> None:
    with pytest.raises(EvidenceRequirementError):
        validate_evidence_requirement("THRESHOLD", ["a", "b"], 0)


def test_threshold_exceeding_claim_ref_count_is_rejected() -> None:
    with pytest.raises(EvidenceRequirementError):
        validate_evidence_requirement("THRESHOLD", ["a"], 5)


def test_threshold_null_for_threshold_mode_is_rejected() -> None:
    with pytest.raises(EvidenceRequirementError):
        validate_evidence_requirement("THRESHOLD", ["a"], None)


@pytest.mark.parametrize("mode", ["ALL", "ANY"])
def test_non_null_threshold_for_all_or_any_is_rejected(mode: str) -> None:
    with pytest.raises(EvidenceRequirementError):
        validate_evidence_requirement(mode, ["a"], 1)


def test_empty_claim_refs_is_rejected_for_every_mode() -> None:
    with pytest.raises(EvidenceRequirementError):
        validate_evidence_requirement("ALL", [], None)
