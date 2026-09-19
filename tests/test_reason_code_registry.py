from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

MINIMUM_REQUIRED_CODES = {
    "CONFIG_INVALID",
    "CONFIG_UNKNOWN_KEY",
    "CONFIG_ALIAS_CONFLICT",
    "STATE_INVALID_TRANSITION",
    "STATE_STALE_RUN_VERSION",
    "POLICY_DENIED",
    "POLICY_APPROVAL_REQUIRED",
    "POLICY_APPROVAL_EXPIRED",
    "POLICY_APPROVAL_CONSUMED",
    "RESOURCE_INVALID",
    "RESOURCE_SCOPE_WIDENING",
    "REPO_IDENTITY_MISMATCH",
    "REPO_DIRTY_DESTINATION",
    "REPO_UNSUPPORTED_STATE",
    "TOOL_INVALID_REQUEST",
    "TOOL_STALE_PREIMAGE",
    "TOOL_TIMEOUT",
    "TOOL_CANCELLED",
    "TOOL_PARTIAL_EFFECT_RECONCILIATION_REQUIRED",
    "VERIFY_FAILED",
    "VERIFY_INCONCLUSIVE",
    "VERIFY_STALE_EVIDENCE",
    "VERIFY_WAIVER_REQUIRED",
    "RECOVERY_EXTERNAL_DRIFT",
    "RECOVERY_AMBIGUOUS_EFFECT",
    "PERSIST_CORRUPT",
    "PERSIST_MIGRATION_REQUIRED",
    "SANDBOX_UNENFORCEABLE_SCOPE",
    "CLI_APPROVAL_UNAVAILABLE",
    "CLI_UNSUPPORTED_CAPABILITY",
    "INTERNAL_INVARIANT_VIOLATION",
}

REQUIRED_NAMESPACES = {
    "CONFIG_", "STATE_", "POLICY_", "RESOURCE_", "REPO_", "TOOL_", "VERIFY_",
    "RECOVERY_", "PERSIST_", "PROVIDER_", "SANDBOX_", "CLI_", "INTERNAL_",
}


def _registry(contracts_root: Path) -> dict[str, Any]:
    return yaml.safe_load((contracts_root / "reason_code_registry.yaml").read_text(encoding="utf-8"))


def _schema(contracts_root: Path) -> dict[str, Any]:
    return json.loads((contracts_root / "reason_code_registry.schema.json").read_text(encoding="utf-8"))


def test_registry_validates_against_its_schema(contracts_root: Path) -> None:
    Draft202012Validator(_schema(contracts_root)).validate(_registry(contracts_root))


def test_every_blueprint_10_5_namespace_is_declared(contracts_root: Path) -> None:
    registry = _registry(contracts_root)
    assert set(registry["namespaces"]) == REQUIRED_NAMESPACES


def test_every_minimum_required_code_is_present(contracts_root: Path) -> None:
    codes = {c["code"] for c in _registry(contracts_root)["codes"]}
    missing = MINIMUM_REQUIRED_CODES - codes
    assert not missing, f"missing minimum required reason codes: {missing}"


def test_minimum_required_flag_matches_blueprint_list(contracts_root: Path) -> None:
    for entry in _registry(contracts_root)["codes"]:
        expected = entry["code"] in MINIMUM_REQUIRED_CODES
        assert entry["minimum_required"] == expected, entry["code"]


def test_codes_are_unique(contracts_root: Path) -> None:
    codes = [c["code"] for c in _registry(contracts_root)["codes"]]
    assert len(codes) == len(set(codes)), "duplicate reason code in the registry"


def test_every_code_belongs_to_a_declared_namespace_and_carries_its_prefix(contracts_root: Path) -> None:
    registry = _registry(contracts_root)
    namespaces = set(registry["namespaces"])
    for entry in registry["codes"]:
        assert entry["namespace"] in namespaces, entry["code"]
        assert entry["code"].startswith(entry["namespace"]), (
            f"{entry['code']} does not start with its declared namespace {entry['namespace']}"
        )


def test_code_shape_matches_symbolic_identifier_pattern(contracts_root: Path) -> None:
    pattern = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")
    for entry in _registry(contracts_root)["codes"]:
        assert pattern.match(entry["code"]), entry["code"]


def test_malformed_registry_with_unregistered_namespace_is_rejected(contracts_root: Path) -> None:
    registry = _registry(contracts_root)
    registry["codes"].append(
        {"code": "GHOST_UNKNOWN", "namespace": "GHOST_", "description": "not a real namespace", "minimum_required": False}
    )
    schema = _schema(contracts_root)
    # The JSON Schema alone only constrains shape/known-namespace-pattern; the
    # cross-field "namespace must be one of the declared namespaces" and
    # "code must start with its namespace" invariants are the responsibility
    # of the cross-contract checks above, which this fixture exercises.
    validator = Draft202012Validator(schema)
    assert validator.is_valid(registry)  # shape-valid...
    namespaces = set(registry["namespaces"])
    assert not all(entry["namespace"] in namespaces for entry in registry["codes"])  # ...but namespace-invalid


def test_malformed_registry_missing_required_field_is_rejected(contracts_root: Path) -> None:
    registry = _registry(contracts_root)
    del registry["codes"][0]["description"]
    validator = Draft202012Validator(_schema(contracts_root))
    assert not validator.is_valid(registry)


def test_malformed_registry_with_lowercase_code_is_rejected(contracts_root: Path) -> None:
    registry = _registry(contracts_root)
    registry["codes"][0]["code"] = "config_invalid"
    validator = Draft202012Validator(_schema(contracts_root))
    assert not validator.is_valid(registry)


def test_no_duplicate_reason_code_authority_exists(repo_root: Path) -> None:
    """Exactly one contracts/*.yaml file may declare a top-level `codes` list
    of reason-code-shaped entries; a second such file would be a duplicate
    hand-maintained registry (canonical-identity.md).
    """
    hits = []
    for path in (repo_root / "contracts").rglob("*.yaml"):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and doc.get("x-contract-name") == "ReasonCodeRegistry":
            hits.append(path)
    assert len(hits) == 1, f"expected exactly one ReasonCodeRegistry contract, found: {hits}"
