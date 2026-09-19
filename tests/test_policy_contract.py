from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from agentic_harness._policy import (
    APPROVAL_BINDING_FIELDS,
    DECISIONS,
    EFFECTS,
    TRUST_CLASSES,
    UNTRUSTED_TRUST_CLASSES,
    ApprovalGrantLike,
    PolicyRule,
    evaluate,
    requires_new_approval,
)

FIXTURES_DIR_NAME = "policy_contract"
_CONTRACTS_ROOT = Path(__file__).resolve().parents[1] / "contracts"


def _schema_doc(contracts_root: Path) -> dict[str, Any]:
    return json.loads((contracts_root / "policy_contract.schema.json").read_text(encoding="utf-8"))


def _registry(contracts_root: Path) -> tuple[Registry, dict[str, Any]]:
    pc = _schema_doc(contracts_root)
    registry = Registry().with_resources([(pc["$id"], Resource.from_contents(pc))])
    return registry, pc


def _validator_for(defname: str, contracts_root: Path) -> Draft202012Validator:
    registry, pc = _registry(contracts_root)
    return Draft202012Validator({"$ref": f"{pc['$id']}#/$defs/{defname}"}, registry=registry)


def _load_fixture(contracts_root: Path, name: str) -> list[dict[str, Any]]:
    path = contracts_root / "tests" / FIXTURES_DIR_NAME / name
    return json.loads(path.read_text(encoding="utf-8"))


def _golden_cases(contracts_root: Path) -> list[tuple[str, Any]]:
    return [(c["def"], c["value"]) for c in _load_fixture(contracts_root, "golden.json")]


def _adversarial_cases(contracts_root: Path) -> list[tuple[str, Any]]:
    return [(c["def"], c["value"]) for c in _load_fixture(contracts_root, "adversarial.json")]


# ---------------------------------------------------------------------------
# Contract structural conformance
# ---------------------------------------------------------------------------


def test_schema_is_valid_draft_2020_12(contracts_root: Path) -> None:
    Draft202012Validator.check_schema(_schema_doc(contracts_root))


def test_fixture_files_exist(contracts_root: Path) -> None:
    assert (contracts_root / "tests" / FIXTURES_DIR_NAME / "golden.json").is_file()
    assert (contracts_root / "tests" / FIXTURES_DIR_NAME / "adversarial.json").is_file()


def test_effects_match_blueprint_9_12_1() -> None:
    assert EFFECTS == {
        "READ", "WORKSPACE_WRITE", "PROCESS_EXEC", "SHELL_INTERPRETATION", "NETWORK",
        "DATA_EGRESS", "EXTERNAL_READ", "EXTERNAL_WRITE", "SECRET_ACCESS", "DESTRUCTIVE", "PRIVILEGED",
    }


def test_trust_classes_match_blueprint_3_7() -> None:
    assert TRUST_CLASSES == {
        "SYSTEM_TRUSTED", "USER_TRUSTED", "PROJECT_POLICY",
        "REPOSITORY_UNTRUSTED", "TOOL_OUTPUT_UNTRUSTED", "EXTERNAL_UNTRUSTED", "MODEL_GENERATED",
    }


def test_decisions_match_blueprint_9_12_5() -> None:
    assert set(DECISIONS) == {"ALLOW", "APPROVAL_REQUIRED", "DENY", "BLOCKED_CAPABILITY"}


@pytest.mark.parametrize("defname,value", _golden_cases(_CONTRACTS_ROOT))
def test_golden_values_validate(defname: str, value: Any, contracts_root: Path) -> None:
    validator = _validator_for(defname, contracts_root)
    errors = sorted(validator.iter_errors(value), key=str)
    assert not errors, f"{defname}: {[e.message for e in errors]}"


@pytest.mark.parametrize("defname,value", _adversarial_cases(_CONTRACTS_ROOT))
def test_adversarial_values_are_rejected(defname: str, value: Any, contracts_root: Path) -> None:
    validator = _validator_for(defname, contracts_root)
    assert not validator.is_valid(value), f"{defname}: {value!r} unexpectedly validated"


# ---------------------------------------------------------------------------
# Decision algebra (9.12.5)
# ---------------------------------------------------------------------------


def test_evaluate_unknown_effect_denies() -> None:
    assert evaluate(effect="TELEPORT", kind="repo_path", normalized_key="src/a.py", rules=[]) == "DENY"


def test_evaluate_unknown_resource_kind_denies() -> None:
    assert evaluate(effect="READ", kind="teleporter", normalized_key="x", rules=[]) == "DENY"


def test_evaluate_no_matching_rule_denies_by_default() -> None:
    assert evaluate(effect="READ", kind="repo_path", normalized_key="src/a.py", rules=[]) == "DENY"


def test_evaluate_explicit_allow_rule() -> None:
    rules = [PolicyRule(authority="SYSTEM_TRUSTED", effect="READ", kind="repo_path", match="PREFIX", value="src/", decision="ALLOW")]
    assert evaluate(effect="READ", kind="repo_path", normalized_key="src/a.py", rules=rules) == "ALLOW"


def test_evaluate_explicit_deny_wins_over_broader_allow() -> None:
    rules = [
        PolicyRule(authority="SYSTEM_TRUSTED", effect="READ", kind="repo_path", match="PREFIX", value="src/", decision="ALLOW"),
        PolicyRule(authority="SYSTEM_TRUSTED", effect="READ", kind="repo_path", match="EXACT", value="src/secret.py", decision="DENY"),
    ]
    assert evaluate(effect="READ", kind="repo_path", normalized_key="src/secret.py", rules=rules) == "DENY"


def test_evaluate_narrower_scope_wins_when_same_specificity_prefers_deny() -> None:
    rules = [
        PolicyRule(authority="SYSTEM_TRUSTED", effect="READ", kind="repo_path", match="EXACT", value="src/a.py", decision="ALLOW"),
        PolicyRule(authority="USER_TRUSTED", effect="READ", kind="repo_path", match="EXACT", value="src/a.py", decision="DENY"),
    ]
    assert evaluate(effect="READ", kind="repo_path", normalized_key="src/a.py", rules=rules) == "DENY"


def test_higher_authority_deny_cannot_be_widened_by_narrower_project_allow() -> None:
    rules = [
        PolicyRule(authority="SYSTEM_TRUSTED", effect="READ", kind="repo_path", match="PREFIX", value="src/", decision="DENY"),
        PolicyRule(authority="PROJECT_POLICY", effect="READ", kind="repo_path", match="EXACT", value="src/a.py", decision="ALLOW"),
    ]
    assert evaluate(effect="READ", kind="repo_path", normalized_key="src/a.py", rules=rules) == "DENY"


def test_evaluate_untrusted_authority_rule_never_participates() -> None:
    rules = [PolicyRule(authority="REPOSITORY_UNTRUSTED", effect="PRIVILEGED", kind="repo_path", match="GLOB", value="**", decision="ALLOW")]
    assert evaluate(effect="PRIVILEGED", kind="repo_path", normalized_key="anything", rules=rules) == "DENY"


def test_evaluate_unenforceable_sandbox_yields_blocked_capability_not_allow() -> None:
    rules = [PolicyRule(authority="SYSTEM_TRUSTED", effect="NETWORK", kind="network_origin", match="EXACT", value="https://api.example.com:443", decision="ALLOW")]
    result = evaluate(effect="NETWORK", kind="network_origin", normalized_key="https://api.example.com:443", rules=rules, sandbox_enforceable=False)
    assert result == "BLOCKED_CAPABILITY"


def test_evaluate_unenforceable_sandbox_does_not_override_a_deny() -> None:
    rules = [PolicyRule(authority="SYSTEM_TRUSTED", effect="NETWORK", kind="network_origin", match="EXACT", value="https://evil.example.com:443", decision="DENY")]
    result = evaluate(effect="NETWORK", kind="network_origin", normalized_key="https://evil.example.com:443", rules=rules, sandbox_enforceable=False)
    assert result == "DENY"


def test_evaluate_approval_required_without_grant() -> None:
    rules = [PolicyRule(authority="SYSTEM_TRUSTED", effect="DESTRUCTIVE", kind="repo_path", match="PREFIX", value="src/", decision="APPROVAL_REQUIRED")]
    assert evaluate(effect="DESTRUCTIVE", kind="repo_path", normalized_key="src/a.py", rules=rules) == "APPROVAL_REQUIRED"


def test_evaluate_approval_required_satisfied_by_matching_grant() -> None:
    rules = [PolicyRule(authority="SYSTEM_TRUSTED", effect="DESTRUCTIVE", kind="repo_path", match="EXACT", value="src/a.py", decision="APPROVAL_REQUIRED")]
    binding = {"effect_set": ["DESTRUCTIVE"]}
    grant = ApprovalGrantLike(disposition="ALLOW_ONCE", binding=binding, consumed=False, expired=False)
    result = evaluate(effect="DESTRUCTIVE", kind="repo_path", normalized_key="src/a.py", rules=rules, approval=grant, request_binding=binding)
    assert result == "ALLOW"


def test_evaluate_consumed_approval_does_not_satisfy_a_new_request() -> None:
    rules = [PolicyRule(authority="SYSTEM_TRUSTED", effect="DESTRUCTIVE", kind="repo_path", match="EXACT", value="src/a.py", decision="APPROVAL_REQUIRED")]
    binding = {"effect_set": ["DESTRUCTIVE"]}
    grant = ApprovalGrantLike(disposition="ALLOW_ONCE", binding=binding, consumed=True, expired=False)
    result = evaluate(effect="DESTRUCTIVE", kind="repo_path", normalized_key="src/a.py", rules=rules, approval=grant, request_binding=binding)
    assert result == "APPROVAL_REQUIRED"


def test_evaluate_approval_cannot_override_a_hard_deny() -> None:
    rules = [PolicyRule(authority="SYSTEM_TRUSTED", effect="DESTRUCTIVE", kind="repo_path", match="EXACT", value="src/a.py", decision="DENY")]
    binding = {"effect_set": ["DESTRUCTIVE"]}
    grant = ApprovalGrantLike(disposition="ALLOW_RUN", binding=binding, consumed=False, expired=False)
    result = evaluate(effect="DESTRUCTIVE", kind="repo_path", normalized_key="src/a.py", rules=rules, approval=grant, request_binding=binding)
    assert result == "DENY"


def test_evaluate_mismatched_approval_binding_does_not_satisfy() -> None:
    rules = [PolicyRule(authority="SYSTEM_TRUSTED", effect="DESTRUCTIVE", kind="repo_path", match="EXACT", value="src/a.py", decision="APPROVAL_REQUIRED")]
    grant = ApprovalGrantLike(disposition="ALLOW_ONCE", binding={"argument_digest": "sha256:" + "a" * 64}, consumed=False, expired=False)
    result = evaluate(
        effect="DESTRUCTIVE", kind="repo_path", normalized_key="src/a.py", rules=rules,
        approval=grant, request_binding={"argument_digest": "sha256:" + "b" * 64},
    )
    assert result == "APPROVAL_REQUIRED"


# ---------------------------------------------------------------------------
# Approval binding / re-approval (9.12.6, INV-APPROVAL-002)
# ---------------------------------------------------------------------------


def test_approval_binding_fields_match_blueprint_9_12_6() -> None:
    assert APPROVAL_BINDING_FIELDS == (
        "effect_set", "normalized_resources", "argument_digest", "credential_exposure",
        "reversibility", "run_id", "tool_call_identity", "tool_schema_digest",
    )


def test_requires_new_approval_false_for_unchanged_request() -> None:
    binding = {"effect_set": ["READ"], "argument_digest": "sha256:" + "a" * 64, "run_id": "r1"}
    assert requires_new_approval(binding, dict(binding)) is False


def test_requires_new_approval_true_when_effect_set_changes() -> None:
    previous = {"effect_set": ["READ"]}
    proposed = {"effect_set": ["READ", "DESTRUCTIVE"]}
    assert requires_new_approval(previous, proposed) is True


def test_requires_new_approval_true_when_resources_change() -> None:
    previous = {"normalized_resources": [{"kind": "repo_path", "normalized_key": "src/a.py"}]}
    proposed = {"normalized_resources": [{"kind": "repo_path", "normalized_key": "src/b.py"}]}
    assert requires_new_approval(previous, proposed) is True


def test_requires_new_approval_ignores_resource_ordering() -> None:
    previous = {"normalized_resources": [{"kind": "repo_path", "normalized_key": "a"}, {"kind": "repo_path", "normalized_key": "b"}]}
    proposed = {"normalized_resources": [{"kind": "repo_path", "normalized_key": "b"}, {"kind": "repo_path", "normalized_key": "a"}]}
    assert requires_new_approval(previous, proposed) is False


def test_untrusted_trust_classes_subset_of_trust_classes() -> None:
    assert UNTRUSTED_TRUST_CLASSES <= TRUST_CLASSES
    assert UNTRUSTED_TRUST_CLASSES == {"REPOSITORY_UNTRUSTED", "TOOL_OUTPUT_UNTRUSTED", "EXTERNAL_UNTRUSTED", "MODEL_GENERATED"}


def test_unknown_rule_authority_cannot_grant_access() -> None:
    rules = [PolicyRule(authority="FUTURE_TRUST_CLASS", effect="READ", kind="repo_path", match="EXACT", value="src/a.py", decision="ALLOW")]
    assert evaluate(effect="READ", kind="repo_path", normalized_key="src/a.py", rules=rules) == "DENY"


def test_malformed_matching_rule_fails_closed() -> None:
    rules = [PolicyRule(authority="SYSTEM_TRUSTED", effect="READ", kind="repo_path", match="EXACT", value="src/a.py", decision="FUTURE_DECISION")]
    assert evaluate(effect="READ", kind="repo_path", normalized_key="src/a.py", rules=rules) == "DENY"


def test_approval_without_request_binding_cannot_satisfy_policy() -> None:
    rules = [PolicyRule(authority="SYSTEM_TRUSTED", effect="DESTRUCTIVE", kind="repo_path", match="EXACT", value="src/a.py", decision="APPROVAL_REQUIRED")]
    grant = ApprovalGrantLike(disposition="ALLOW_RUN", binding={}, consumed=False, expired=False)
    assert evaluate(effect="DESTRUCTIVE", kind="repo_path", normalized_key="src/a.py", rules=rules, approval=grant) == "APPROVAL_REQUIRED"


def test_data_classification_above_explicit_egress_ceiling_denies() -> None:
    rules = [PolicyRule(authority="SYSTEM_TRUSTED", effect="DATA_EGRESS", kind="external_service", match="EXACT", value="sink", decision="ALLOW")]
    assert evaluate(
        effect="DATA_EGRESS", kind="external_service", normalized_key="sink", rules=rules,
        data_classification="SECRET", maximum_classification="PUBLIC",
    ) == "DENY"


def test_unknown_taint_denies_policy_request() -> None:
    assert evaluate(effect="READ", kind="repo_path", normalized_key="src/a.py", rules=[], taint=frozenset({"UNKNOWN"})) == "DENY"
