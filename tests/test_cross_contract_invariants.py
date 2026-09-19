from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from agentic_harness import _invariants as inv

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


# ---------------------------------------------------------------------------
# Registry structural conformance
# ---------------------------------------------------------------------------


def _registry_doc(contracts_root: Path) -> dict[str, Any]:
    with (contracts_root / "cross_contract_invariant_registry.yaml").open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _schema_doc(contracts_root: Path) -> dict[str, Any]:
    return json.loads((contracts_root / "cross_contract_invariant_registry.schema.json").read_text(encoding="utf-8"))


def test_registry_schema_is_valid_draft_2020_12(contracts_root: Path) -> None:
    Draft202012Validator.check_schema(_schema_doc(contracts_root))


def test_registry_document_validates_against_its_schema(contracts_root: Path) -> None:
    validator = Draft202012Validator(_schema_doc(contracts_root))
    errors = sorted(validator.iter_errors(_registry_doc(contracts_root)), key=str)
    assert not errors, [e.message for e in errors]


def test_registry_contains_exactly_the_blueprint_minimum_set(contracts_root: Path) -> None:
    doc = _registry_doc(contracts_root)
    ids = {entry["id"] for entry in doc["invariants"]}
    assert ids == {
        "INV-IDENTITY-001", "INV-IDENTITY-002",
        "INV-GOAL-001",
        "INV-REVISION-001",
        "INV-APPROVAL-001", "INV-APPROVAL-002",
        "INV-STATE-001", "INV-STATE-002",
        "INV-ACCEPT-001",
        "INV-SECURITY-001", "INV-SECURITY-002",
        "INV-RESOURCE-001",
        "INV-WORKTREE-001",
        "INV-EVENT-001", "INV-EVENT-002",
        "INV-TOOL-001",
        "INV-VERIFY-001", "INV-VERIFY-002",
        "INV-SECRET-001",
    }


def test_every_required_invariant_has_a_test_mapping(contracts_root: Path) -> None:
    doc = _registry_doc(contracts_root)
    for entry in doc["invariants"]:
        if entry["required"]:
            assert entry["test_refs"], f"{entry['id']} is required but has no test_refs"


def test_no_invariant_is_falsely_claimed_runtime_enforced(contracts_root: Path) -> None:
    """At this phase slice no runtime component exists to call any checker (Phase 1-3
    deliverables); every entry MUST honestly report AWAITING_RUNTIME_INTEGRATION rather
    than overclaim enforcement that isn't wired up yet."""
    doc = _registry_doc(contracts_root)
    for entry in doc["invariants"]:
        assert entry["enforcement_status"] == "AWAITING_RUNTIME_INTEGRATION", entry["id"]


def test_every_test_ref_resolves_to_a_collected_test_in_this_module(contracts_root: Path) -> None:
    doc = _registry_doc(contracts_root)
    this_module_names = {name for name in globals() if name.startswith("test_")}
    for entry in doc["invariants"]:
        for ref in entry["test_refs"]:
            assert ref.startswith("tests/test_cross_contract_invariants.py::"), ref
            func_name = ref.split("::", 1)[1]
            assert func_name in this_module_names, f"{entry['id']}: {func_name} is not defined in this test module"


def test_every_checker_ref_resolves_to_an_invariants_module_function(contracts_root: Path) -> None:
    doc = _registry_doc(contracts_root)
    for entry in doc["invariants"]:
        checker_ref = entry.get("checker_ref")
        if checker_ref is None:
            continue
        assert checker_ref.startswith("agentic_harness._invariants.")
        func_name = checker_ref.rsplit(".", 1)[1]
        assert hasattr(inv, func_name), f"{entry['id']}: {checker_ref} does not exist"
        assert inv.CHECKERS[entry["id"]] is getattr(inv, func_name)


def test_checkers_registry_covers_every_registry_entry(contracts_root: Path) -> None:
    doc = _registry_doc(contracts_root)
    ids_with_checker = {entry["id"] for entry in doc["invariants"] if entry.get("checker_ref")}
    assert set(inv.CHECKERS) == ids_with_checker


# ---------------------------------------------------------------------------
# INV-IDENTITY-001
# ---------------------------------------------------------------------------


def test_inv_identity_001_matching_snapshot_satisfies() -> None:
    assert inv.inv_identity_001(DIGEST_A, DIGEST_A) is True


def test_inv_identity_001_mismatched_snapshot_violates() -> None:
    assert inv.inv_identity_001(DIGEST_A, DIGEST_B) is False


# ---------------------------------------------------------------------------
# INV-IDENTITY-002
# ---------------------------------------------------------------------------


def test_inv_identity_002_matching_governed_state_satisfies() -> None:
    assert inv.inv_identity_002("change-rev-1", "change-rev-1", DIGEST_A, DIGEST_A) is True


def test_inv_identity_002_stale_change_revision_violates() -> None:
    assert inv.inv_identity_002("change-rev-1", "change-rev-2", DIGEST_A, DIGEST_A) is False


# ---------------------------------------------------------------------------
# INV-GOAL-001
# ---------------------------------------------------------------------------


def test_inv_goal_001_known_revision_in_same_run_satisfies() -> None:
    known = {("goal-rev-1", "run-1")}
    assert inv.inv_goal_001("goal-rev-1", "run-1", known) is True


def test_inv_goal_001_unknown_revision_violates() -> None:
    known = {("goal-rev-1", "run-1")}
    assert inv.inv_goal_001("goal-rev-2", "run-1", known) is False
    assert inv.inv_goal_001("goal-rev-1", "run-2", known) is False


# ---------------------------------------------------------------------------
# INV-REVISION-001
# ---------------------------------------------------------------------------


def test_inv_revision_001_unchanged_identity_stays_current() -> None:
    assert inv.inv_revision_001("change-rev-1", "change-rev-1") is True


def test_inv_revision_001_changed_identity_is_invalidated() -> None:
    assert inv.inv_revision_001("change-rev-1", "change-rev-2") is False


# ---------------------------------------------------------------------------
# INV-APPROVAL-001
# ---------------------------------------------------------------------------


def test_inv_approval_001_matching_request_digest_satisfies() -> None:
    assert inv.inv_approval_001(DIGEST_A, DIGEST_A) is True


def test_inv_approval_001_mismatched_request_digest_violates() -> None:
    assert inv.inv_approval_001(DIGEST_A, DIGEST_B) is False


# ---------------------------------------------------------------------------
# INV-APPROVAL-002
# ---------------------------------------------------------------------------


def _approval_request(**overrides: Any) -> dict[str, Any]:
    base = {
        "effects": ["WORKSPACE_WRITE"],
        "resources": [{"kind": "PATH", "normalized_key": "src/x.py"}],
        "argument_digest": DIGEST_A,
        "credential_exposure": "NONE",
        "reversibility": "REVERSIBLE",
        "tool_schema_digest": DIGEST_A,
    }
    base.update(overrides)
    return base


def test_inv_approval_002_unchanged_request_does_not_require_new_approval() -> None:
    previous = _approval_request()
    proposed = _approval_request()
    assert inv.inv_approval_002(previous, proposed) is False


def test_inv_approval_002_changed_effects_require_new_approval() -> None:
    previous = _approval_request()
    proposed = _approval_request(effects=["WORKSPACE_WRITE", "NETWORK"])
    assert inv.inv_approval_002(previous, proposed) is True


# ---------------------------------------------------------------------------
# INV-STATE-001
# ---------------------------------------------------------------------------


def test_inv_state_001_canonical_forward_transition_satisfies() -> None:
    assert inv.inv_state_001("CREATED", "bind_repository", "REPOSITORY_READY") is True


def test_inv_state_001_exceptional_transition_from_nonterminal_satisfies() -> None:
    assert inv.inv_state_001("IMPLEMENTING", "block", "BLOCKED") is True


def test_inv_state_001_unregistered_transition_violates() -> None:
    assert inv.inv_state_001("CREATED", "accept", "ACCEPTING") is False


def test_inv_state_001_transition_from_terminal_state_violates() -> None:
    assert inv.inv_state_001("ACCEPTED", "block", "BLOCKED") is False


# ---------------------------------------------------------------------------
# INV-STATE-002
# ---------------------------------------------------------------------------


def test_inv_state_002_all_mandatory_criteria_satisfied() -> None:
    assert inv.inv_state_002({"AC-1", "AC-2"}, {"AC-1": "SATISFIED", "AC-2": "WAIVED"}) is True


def test_inv_state_002_unsatisfied_mandatory_criterion_violates() -> None:
    assert inv.inv_state_002({"AC-1", "AC-2"}, {"AC-1": "SATISFIED", "AC-2": "UNSATISFIED"}) is False


# ---------------------------------------------------------------------------
# INV-ACCEPT-001
# ---------------------------------------------------------------------------


def test_inv_accept_001_completed_integration_and_passing_checks_satisfies() -> None:
    assert inv.inv_accept_001("COMPLETED", True) is True


def test_inv_accept_001_incomplete_integration_violates() -> None:
    assert inv.inv_accept_001("STARTED", True) is False
    assert inv.inv_accept_001("COMPLETED", False) is False


# ---------------------------------------------------------------------------
# INV-SECURITY-001
# ---------------------------------------------------------------------------


def test_inv_security_001_within_intersection_satisfies() -> None:
    effective = frozenset({"READ"})
    bound_a = frozenset({"READ", "WORKSPACE_WRITE"})
    bound_b = frozenset({"READ", "NETWORK"})
    assert inv.inv_security_001(effective, bound_a, bound_b) is True


def test_inv_security_001_exceeding_intersection_violates() -> None:
    effective = frozenset({"WORKSPACE_WRITE"})
    bound_a = frozenset({"READ", "WORKSPACE_WRITE"})
    bound_b = frozenset({"READ"})
    assert inv.inv_security_001(effective, bound_a, bound_b) is False


# ---------------------------------------------------------------------------
# INV-SECURITY-002
# ---------------------------------------------------------------------------


def test_inv_security_002_untrusted_claim_cannot_expand_capabilities() -> None:
    base = frozenset({"READ"})
    claimed = frozenset({"READ", "PRIVILEGED", "SECRET_ACCESS"})
    assert inv.inv_security_002(base, claimed) == base


# ---------------------------------------------------------------------------
# INV-RESOURCE-001
# ---------------------------------------------------------------------------


def test_inv_resource_001_correct_order_satisfies() -> None:
    assert inv.inv_resource_001(("NORMALIZE", "AUTHORIZE", "EFFECT")) is True


def test_inv_resource_001_effect_before_authorization_violates() -> None:
    assert inv.inv_resource_001(("NORMALIZE", "EFFECT", "AUTHORIZE")) is False
    assert inv.inv_resource_001(("AUTHORIZE", "NORMALIZE", "EFFECT")) is False


# ---------------------------------------------------------------------------
# INV-WORKTREE-001
# ---------------------------------------------------------------------------


def test_inv_worktree_001_call_targeting_run_worktree_satisfies() -> None:
    assert inv.inv_worktree_001("wt-run-1", "wt-run-1", "checkout-orig") is True


def test_inv_worktree_001_call_targeting_original_checkout_violates() -> None:
    assert inv.inv_worktree_001("wt-run-1", "checkout-orig", "checkout-orig") is False


# ---------------------------------------------------------------------------
# INV-EVENT-001
# ---------------------------------------------------------------------------


def test_inv_event_001_mutation_with_committed_event_satisfies() -> None:
    assert inv.inv_event_001(True, True, True) is True
    assert inv.inv_event_001(False, False, False) is True


def test_inv_event_001_mutation_without_committed_event_violates() -> None:
    assert inv.inv_event_001(True, False, True) is False
    assert inv.inv_event_001(True, True, False) is False


# ---------------------------------------------------------------------------
# INV-EVENT-002
# ---------------------------------------------------------------------------


def test_inv_event_002_strictly_increasing_sequence_satisfies() -> None:
    assert inv.inv_event_002([1, 2, 3, 4]) is True
    assert inv.inv_event_002([1]) is True
    assert inv.inv_event_002([]) is True


def test_inv_event_002_duplicate_sequence_violates() -> None:
    assert inv.inv_event_002([1, 2, 2, 3]) is False
    assert inv.inv_event_002([2, 1, 3]) is False


# ---------------------------------------------------------------------------
# INV-TOOL-001
# ---------------------------------------------------------------------------


def test_inv_tool_001_success_with_atomicity_met_satisfies() -> None:
    assert inv.inv_tool_001(True, "SUCCESS") is True
    assert inv.inv_tool_001(False, "FAILURE") is True


def test_inv_tool_001_success_without_atomicity_violates() -> None:
    assert inv.inv_tool_001(False, "SUCCESS") is False


# ---------------------------------------------------------------------------
# INV-VERIFY-001
# ---------------------------------------------------------------------------


def test_inv_verify_001_runnable_check_may_pass() -> None:
    assert inv.inv_verify_001(True, True, "PASS") is True


def test_inv_verify_001_unrunnable_mandatory_check_cannot_pass() -> None:
    assert inv.inv_verify_001(True, False, "PASS") is False
    assert inv.inv_verify_001(True, False, "INCONCLUSIVE") is True


# ---------------------------------------------------------------------------
# INV-VERIFY-002
# ---------------------------------------------------------------------------


def test_inv_verify_002_unchanged_dependencies_remain_current() -> None:
    bound = {"CANDIDATE_SNAPSHOT": DIGEST_A, "CONFIG_DIGEST": DIGEST_B}
    current = {"CANDIDATE_SNAPSHOT": DIGEST_A, "CONFIG_DIGEST": DIGEST_B}
    assert inv.inv_verify_002(bound, current) is True


def test_inv_verify_002_changed_candidate_snapshot_invalidates() -> None:
    bound = {"CANDIDATE_SNAPSHOT": DIGEST_A}
    current = {"CANDIDATE_SNAPSHOT": DIGEST_B}
    assert inv.inv_verify_002(bound, current) is False


def test_inv_verify_002_candidate_independent_check_survives_mutation() -> None:
    bound = {"CANDIDATE_SNAPSHOT": DIGEST_A}
    current = {"CANDIDATE_SNAPSHOT": DIGEST_B}
    assert inv.inv_verify_002(bound, current, candidate_independent=True) is True


# ---------------------------------------------------------------------------
# INV-SECRET-001
# ---------------------------------------------------------------------------


def test_inv_secret_001_payload_without_secret_satisfies() -> None:
    payload = {"message": "hello world", "nested": {"a": ["b", "c"]}}
    assert inv.inv_secret_001(payload, frozenset({"sk-super-secret"})) is True


def test_inv_secret_001_nested_secret_leak_violates() -> None:
    payload = {"message": "hello", "nested": {"a": ["value=sk-super-secret"]}}
    assert inv.inv_secret_001(payload, frozenset({"sk-super-secret"})) is False


@pytest.mark.parametrize("category", ["IDENTITY", "GOAL", "REVISION", "APPROVAL", "STATE", "ACCEPT", "SECURITY", "RESOURCE", "WORKTREE", "EVENT", "TOOL", "VERIFY", "SECRET"])
def test_every_declared_category_has_at_least_one_invariant(category: str, contracts_root: Path) -> None:
    doc = _registry_doc(contracts_root)
    assert any(entry["category"] == category for entry in doc["invariants"]), category
