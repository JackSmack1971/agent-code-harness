from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from agentic_harness import _state_machine as sm
from agentic_harness._identity import uuid7_str

DIGEST_A = "sha256:" + "a" * 64


def _schema_doc(contracts_root: Path) -> dict[str, Any]:
    return json.loads((contracts_root / "state_machine.schema.json").read_text(encoding="utf-8"))


def _data_doc(contracts_root: Path) -> dict[str, Any]:
    return yaml.safe_load((contracts_root / "state_machine.yaml").read_text(encoding="utf-8"))


def _fixture(contracts_root: Path, name: str) -> list[dict[str, Any]]:
    return json.loads((contracts_root / "tests" / "state_machine" / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Contract structural conformance
# ---------------------------------------------------------------------------


def test_schema_is_valid_draft_2020_12(contracts_root: Path) -> None:
    Draft202012Validator.check_schema(_schema_doc(contracts_root))


def test_data_document_validates_against_its_schema(contracts_root: Path) -> None:
    # Exercised end-to-end (with the semantic_types.schema.json $ref registry
    # wired up) through the runtime loader, which is the actual contract.
    doc = sm.load_state_machine(contracts_root)
    assert doc["x-contract-name"] == "StateMachine"


def test_fixture_files_exist(contracts_root: Path) -> None:
    assert (contracts_root / "tests" / "state_machine" / "golden.json").is_file()
    assert (contracts_root / "tests" / "state_machine" / "adversarial.json").is_file()


def test_states_match_blueprint_3_4_registry(contracts_root: Path) -> None:
    doc = _data_doc(contracts_root)
    assert doc["states"] == [
        "CREATED", "REPOSITORY_READY", "GOAL_BOUND", "RECONNAISSANCE", "PLAN_READY",
        "IMPLEMENTING", "VERIFYING_FOCUSED", "VERIFYING_BROAD", "INTENT_REVIEW",
        "READY_FOR_USER", "ACCEPTING", "ACCEPTED", "REJECTED", "BLOCKED",
        "INTEGRATION_CONFLICT", "RECOVERY_REQUIRED", "RECONCILIATION_REQUIRED",
        "FAILED", "INTERRUPTED",
    ]


def test_terminal_states_are_exactly_accepted_rejected_failed(contracts_root: Path) -> None:
    doc = _data_doc(contracts_root)
    assert set(doc["terminal_states"]) == {"ACCEPTED", "REJECTED", "FAILED"}


def test_forward_transition_table_has_exactly_17_rows(contracts_root: Path) -> None:
    doc = _data_doc(contracts_root)
    assert len(doc["forward_transitions"]) == 17


def test_exceptional_transitions_have_exactly_5_entries(contracts_root: Path) -> None:
    doc = _data_doc(contracts_root)
    entries = doc["exceptional_transitions"]["entries"]
    assert {e["command"] for e in entries} == {"block", "interrupt", "require_recovery", "require_reconciliation", "fail"}
    assert {e["to"] for e in entries} == {"BLOCKED", "INTERRUPTED", "RECOVERY_REQUIRED", "RECONCILIATION_REQUIRED", "FAILED"}


def test_recovery_transitions_cover_every_recoverable_source_state(contracts_root: Path) -> None:
    doc = _data_doc(contracts_root)
    covered = {r["source_state"] for r in doc["recovery_transitions"]}
    assert covered == sm.RECOVERABLE_SOURCE_STATES


def test_no_recovery_relation_ever_targets_accepted(contracts_root: Path) -> None:
    doc = _data_doc(contracts_root)
    for relation in doc["recovery_transitions"]:
        for branch in relation.get("branches", []):
            assert branch["to"] != "ACCEPTED"


# ---------------------------------------------------------------------------
# Fixture-driven conformance (every fixture-listed transition/recovery is
# explicitly authorized or explicitly rejected)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "entry",
    _fixture(Path(__file__).resolve().parents[1] / "contracts", "golden.json"),
    ids=lambda e: f"{e['kind']}:{e.get('from', e.get('source_state'))}:{e.get('command')}",
)
def test_golden_fixture_entries_are_authorized(entry: dict[str, Any], contracts_root: Path) -> None:
    if entry["kind"] == "transition":
        assert sm.is_valid_transition(entry["from"], entry["command"], entry["to"], contracts_root=contracts_root) is True
    else:
        doc = sm.load_state_machine(contracts_root)
        relation = next(r for r in doc["recovery_transitions"] if r["source_state"] == entry["source_state"])
        assert relation["target_mode"] == entry["target_mode"]
        if entry["target_mode"] == "FIXED_BY_DISPOSITION":
            branch = next(b for b in relation["branches"] if b["disposition"] == entry["disposition"])
            assert branch["to"] == entry["to"]
            assert branch["command"] == entry["command"]
        else:
            assert relation["command"] == entry["command"]


@pytest.mark.parametrize(
    "entry",
    _fixture(Path(__file__).resolve().parents[1] / "contracts", "adversarial.json"),
    ids=lambda e: f"{e['kind']}:{e.get('from', e.get('current_state'))}:{e.get('command', e.get('disposition'))}",
)
def test_adversarial_fixture_entries_are_rejected(entry: dict[str, Any], contracts_root: Path) -> None:
    if entry["kind"] == "transition":
        assert sm.is_valid_transition(entry["from"], entry["command"], entry["to"], contracts_root=contracts_root) is False
    elif entry["kind"] == "resume":
        result = sm.authorize_resume(
            current_state=entry["current_state"],
            current_run_version=1,
            expected_run_version=1,
            resume_target_state="CREATED",
            last_safe_checkpoint_state="CREATED",
            disposition=entry.get("disposition"),
            conditions_satisfied=None,
            contracts_root=contracts_root,
        )
        assert isinstance(result, sm.ResumeRejected)
        assert result.reason_code in (sm.REASON_STATE_INVALID_TRANSITION, "RECOVERY_EXTERNAL_DRIFT")
    else:
        assert entry["kind"] == "resume_target_is_accepted"
        with pytest.raises(sm.StateMachineError) as exc_info:
            sm.authorize_resume(
                current_state=entry["current_state"],
                current_run_version=1,
                expected_run_version=1,
                resume_target_state=entry["resume_target_state"],
                conditions_satisfied={"blocker_reason_no_longer_true": True, "all_pre_block_guards_revalidate": True},
                contracts_root=contracts_root,
            )
        assert exc_info.value.reason_code == sm.REASON_INTERNAL_INVARIANT_VIOLATION


# ---------------------------------------------------------------------------
# Property test: every (state, command, state) combination is EXPLICITLY
# valid or EXPLICITLY rejected -- no undefined behavior.
# ---------------------------------------------------------------------------

_ALL_COMMANDS = [
    "bind_repository", "bind_goal", "begin_reconnaissance", "finalize_plan",
    "begin_implementation", "begin_focused_verification", "focused_passed", "repair",
    "broad_passed", "review_passed", "accept", "reject", "integration_verified",
    "integration_conflict", "destination_drift",
    "block", "interrupt", "require_recovery", "require_reconciliation", "fail",
    "not_a_real_command",
]


def test_every_state_command_state_combination_is_explicitly_decided(contracts_root: Path) -> None:
    doc = sm.load_state_machine(contracts_root)
    states = doc["states"]
    forward_pairs = {(row["from"], row["command"]): row["to"] for row in doc["forward_transitions"]}
    exceptional_targets = {e["command"]: e["to"] for e in doc["exceptional_transitions"]["entries"]}
    terminal = set(doc["terminal_states"])

    decided = 0
    for from_state, command, to_state in itertools.product(states, _ALL_COMMANDS, states):
        expected: bool
        if (from_state, command) in forward_pairs:
            expected = forward_pairs[(from_state, command)] == to_state
        elif from_state not in terminal and command in exceptional_targets:
            expected = exceptional_targets[command] == to_state
        else:
            expected = False
        assert sm.is_valid_transition(from_state, command, to_state, contracts_root=contracts_root) is expected
        decided += 1

    assert decided == len(states) * len(_ALL_COMMANDS) * len(states)


# ---------------------------------------------------------------------------
# authorize_transition: optimistic concurrency, from_state binding, guard gates
# ---------------------------------------------------------------------------


def _transition_command(**overrides: Any) -> dict[str, Any]:
    base = {
        "transition_id": uuid7_str(),
        "run_id": uuid7_str(),
        "from_state": "CREATED",
        "to_state": "REPOSITORY_READY",
        "command": "bind_repository",
        "expected_run_version": 0,
        "precondition_evidence": [DIGEST_A],
        "requested_at": "2026-09-19T00:00:00Z",
    }
    base.update(overrides)
    return base


def test_authorize_transition_commits_a_valid_request(contracts_root: Path) -> None:
    result = sm.authorize_transition(
        _transition_command(),
        current_state="CREATED",
        current_run_version=0,
        contracts_root=contracts_root,
    )
    assert isinstance(result, sm.TransitionCommitted)
    assert result.to_state == "REPOSITORY_READY"
    assert result.new_run_version == 1


def test_authorize_transition_rejects_stale_run_version_without_mutating(contracts_root: Path) -> None:
    result = sm.authorize_transition(
        _transition_command(expected_run_version=0),
        current_state="CREATED",
        current_run_version=5,
        contracts_root=contracts_root,
    )
    assert isinstance(result, sm.TransitionRejected)
    assert result.reason_code == sm.REASON_STATE_STALE_RUN_VERSION


def test_authorize_transition_rejects_mismatched_from_state(contracts_root: Path) -> None:
    result = sm.authorize_transition(
        _transition_command(from_state="GOAL_BOUND", to_state="RECONNAISSANCE", command="begin_reconnaissance", expected_run_version=0),
        current_state="CREATED",
        current_run_version=0,
        contracts_root=contracts_root,
    )
    assert isinstance(result, sm.TransitionRejected)
    assert result.reason_code == sm.REASON_STATE_INVALID_TRANSITION


def test_authorize_transition_rejects_unregistered_transition(contracts_root: Path) -> None:
    result = sm.authorize_transition(
        _transition_command(to_state="ACCEPTING", command="accept", expected_run_version=0),
        current_state="CREATED",
        current_run_version=0,
        contracts_root=contracts_root,
    )
    assert isinstance(result, sm.TransitionRejected)
    assert result.reason_code == sm.REASON_STATE_INVALID_TRANSITION


def test_authorize_transition_raises_on_malformed_request(contracts_root: Path) -> None:
    malformed = _transition_command()
    del malformed["run_id"]
    with pytest.raises(sm.StateMachineError):
        sm.authorize_transition(malformed, current_state="CREATED", current_run_version=0, contracts_root=contracts_root)


def test_ready_for_user_guard_cannot_be_bypassed_by_omission(contracts_root: Path) -> None:
    request = _transition_command(
        from_state="INTENT_REVIEW", to_state="READY_FOR_USER", command="review_passed", expected_run_version=0,
    )
    result = sm.authorize_transition(request, current_state="INTENT_REVIEW", current_run_version=0, contracts_root=contracts_root)
    assert isinstance(result, sm.TransitionRejected)
    assert result.reason_code == sm.REASON_STATE_INVALID_TRANSITION


def test_ready_for_user_guard_rejects_unsatisfied_criteria(contracts_root: Path) -> None:
    request = _transition_command(
        from_state="INTENT_REVIEW", to_state="READY_FOR_USER", command="review_passed", expected_run_version=0,
    )
    result = sm.authorize_transition(
        request,
        current_state="INTENT_REVIEW",
        current_run_version=0,
        guard_context={"mandatory_criterion_ids": {"AC-1"}, "criterion_evaluations": {"AC-1": "UNSATISFIED"}},
        contracts_root=contracts_root,
    )
    assert isinstance(result, sm.TransitionRejected)


def test_ready_for_user_guard_commits_with_satisfied_criteria(contracts_root: Path) -> None:
    request = _transition_command(
        from_state="INTENT_REVIEW", to_state="READY_FOR_USER", command="review_passed", expected_run_version=0,
    )
    result = sm.authorize_transition(
        request,
        current_state="INTENT_REVIEW",
        current_run_version=0,
        guard_context={"mandatory_criterion_ids": {"AC-1"}, "criterion_evaluations": {"AC-1": "SATISFIED"}},
        contracts_root=contracts_root,
    )
    assert isinstance(result, sm.TransitionCommitted)


def test_accepted_guard_cannot_be_bypassed_by_omission(contracts_root: Path) -> None:
    request = _transition_command(
        from_state="ACCEPTING", to_state="ACCEPTED", command="integration_verified", expected_run_version=3,
    )
    result = sm.authorize_transition(request, current_state="ACCEPTING", current_run_version=3, contracts_root=contracts_root)
    assert isinstance(result, sm.TransitionRejected)
    assert result.reason_code == sm.REASON_STATE_INVALID_TRANSITION


def test_accepted_guard_rejects_incomplete_integration(contracts_root: Path) -> None:
    request = _transition_command(
        from_state="ACCEPTING", to_state="ACCEPTED", command="integration_verified", expected_run_version=3,
    )
    result = sm.authorize_transition(
        request,
        current_state="ACCEPTING",
        current_run_version=3,
        guard_context={"integration_status": "STARTED", "post_integration_checks_passed": True},
        contracts_root=contracts_root,
    )
    assert isinstance(result, sm.TransitionRejected)


def test_accepted_guard_commits_with_completed_integration(contracts_root: Path) -> None:
    request = _transition_command(
        from_state="ACCEPTING", to_state="ACCEPTED", command="integration_verified", expected_run_version=3,
    )
    result = sm.authorize_transition(
        request,
        current_state="ACCEPTING",
        current_run_version=3,
        guard_context={"integration_status": "COMPLETED", "post_integration_checks_passed": True},
        contracts_root=contracts_root,
    )
    assert isinstance(result, sm.TransitionCommitted)
    assert result.to_state == "ACCEPTED"


# ---------------------------------------------------------------------------
# authorize_resume: recovery relation, idempotency, ACCEPTED refusal
# ---------------------------------------------------------------------------


def test_resume_rejected_when_run_already_active(contracts_root: Path) -> None:
    result = sm.authorize_resume(
        current_state="IMPLEMENTING", current_run_version=0, expected_run_version=0, contracts_root=contracts_root,
    )
    assert isinstance(result, sm.ResumeRejected)
    assert result.reason_code == sm.REASON_STATE_INVALID_TRANSITION


def test_resume_rejected_on_stale_run_version(contracts_root: Path) -> None:
    result = sm.authorize_resume(
        current_state="BLOCKED", current_run_version=5, expected_run_version=1, contracts_root=contracts_root,
    )
    assert isinstance(result, sm.ResumeRejected)
    assert result.reason_code == sm.REASON_STATE_STALE_RUN_VERSION


def test_resume_repeated_while_blocked_is_idempotent_and_preserves_blocker_classification(contracts_root: Path) -> None:
    kwargs = dict(
        current_state="BLOCKED",
        current_run_version=2,
        expected_run_version=2,
        resume_target_state="IMPLEMENTING",
        conditions_satisfied={"blocker_reason_no_longer_true": False, "all_pre_block_guards_revalidate": False},
        blocker_reason_code="RECOVERY_EXTERNAL_DRIFT",
        contracts_root=contracts_root,
    )
    first = sm.authorize_resume(**kwargs)
    second = sm.authorize_resume(**kwargs)
    assert first == second
    assert isinstance(first, sm.ResumeRejected)
    assert first.blocker_reason_code == "RECOVERY_EXTERNAL_DRIFT"


def test_resume_succeeds_once_all_conditions_satisfied(contracts_root: Path) -> None:
    result = sm.authorize_resume(
        current_state="BLOCKED",
        current_run_version=2,
        expected_run_version=2,
        resume_target_state="IMPLEMENTING",
        conditions_satisfied={"blocker_reason_no_longer_true": True, "all_pre_block_guards_revalidate": True},
        contracts_root=contracts_root,
    )
    assert isinstance(result, sm.ResumeCommitted)
    assert result.to_state == "IMPLEMENTING"
    assert result.new_run_version == 3


def test_resume_recovery_required_uses_last_safe_checkpoint(contracts_root: Path) -> None:
    result = sm.authorize_resume(
        current_state="RECOVERY_REQUIRED",
        current_run_version=4,
        expected_run_version=4,
        last_safe_checkpoint_state="VERIFYING_FOCUSED",
        conditions_satisfied={"every_incomplete_side_effect_transaction_classified_applied_not_applied_or_reconciled": True},
        contracts_root=contracts_root,
    )
    assert isinstance(result, sm.ResumeCommitted)
    assert result.to_state == "VERIFYING_FOCUSED"


def test_resume_integration_conflict_unchanged_destination_returns_to_ready_for_user(contracts_root: Path) -> None:
    result = sm.authorize_resume(
        current_state="INTEGRATION_CONFLICT",
        current_run_version=6,
        expected_run_version=6,
        disposition="DESTINATION_UNCHANGED_CANDIDATE_VALID",
        conditions_satisfied={"disposition_explicitly_recorded": True},
        contracts_root=contracts_root,
    )
    assert isinstance(result, sm.ResumeCommitted)
    assert result.to_state == "READY_FOR_USER"
    assert result.command == "resolve_conflict_unchanged"


def test_resume_integration_conflict_new_candidate_goes_to_implementing(contracts_root: Path) -> None:
    result = sm.authorize_resume(
        current_state="INTEGRATION_CONFLICT",
        current_run_version=6,
        expected_run_version=6,
        disposition="NEW_CANDIDATE_CREATED",
        conditions_satisfied={"disposition_explicitly_recorded": True},
        contracts_root=contracts_root,
    )
    assert isinstance(result, sm.ResumeCommitted)
    assert result.to_state == "IMPLEMENTING"


def test_resume_integration_conflict_abandonment_goes_to_rejected(contracts_root: Path) -> None:
    result = sm.authorize_resume(
        current_state="INTEGRATION_CONFLICT",
        current_run_version=6,
        expected_run_version=6,
        disposition="AUTHORIZED_ABANDONMENT",
        conditions_satisfied={"disposition_explicitly_recorded": True},
        contracts_root=contracts_root,
    )
    assert isinstance(result, sm.ResumeCommitted)
    assert result.to_state == "REJECTED"


def test_resume_integration_conflict_never_authorizes_accepted(contracts_root: Path) -> None:
    doc = sm.load_state_machine(contracts_root)
    relation = next(r for r in doc["recovery_transitions"] if r["source_state"] == "INTEGRATION_CONFLICT")
    assert all(b["to"] != "ACCEPTED" for b in relation["branches"])


def test_resume_target_resolving_to_accepted_raises_instead_of_committing(contracts_root: Path) -> None:
    with pytest.raises(sm.StateMachineError) as exc_info:
        sm.authorize_resume(
            current_state="BLOCKED",
            current_run_version=1,
            expected_run_version=1,
            resume_target_state="ACCEPTED",
            conditions_satisfied={"blocker_reason_no_longer_true": True, "all_pre_block_guards_revalidate": True},
            contracts_root=contracts_root,
        )
    assert exc_info.value.reason_code == sm.REASON_INTERNAL_INVARIANT_VIOLATION


def test_resume_missing_persisted_target_is_rejected_not_a_crash(contracts_root: Path) -> None:
    result = sm.authorize_resume(
        current_state="BLOCKED",
        current_run_version=1,
        expected_run_version=1,
        resume_target_state=None,
        contracts_root=contracts_root,
    )
    assert isinstance(result, sm.ResumeRejected)
