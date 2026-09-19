"""Pure-function reference checkers for `CrossContractInvariantRegistry v1` (Blueprint 9.7).

Each function decides exactly the predicate its `INV-*` invariant states,
over already-validated `DomainSchemas v1` field values (or the minimal
primitive facts a later runtime component would supply). None of these
functions perform I/O, persistence, or side effects: the full runtime
enforcement (transactional journaling, worktree isolation, sandboxed
execution, policy engine) belongs to Phase 1-3 components that do not exist
yet. What is verifiable now is the decidable logic each invariant is built
from; `tests/test_cross_contract_invariants.py` exercises every function
here against both a satisfying and a violating case.

`contracts/cross_contract_invariant_registry.yaml` is the sole authoritative
registry of invariant IDs/metadata; this module is deliberately not a
second copy of that data, only the executable logic each ID maps to.
"""

from __future__ import annotations

from typing import Any

from ._canonical import canonical_json_bytes

# ---------------------------------------------------------------------------
# IDENTITY
# ---------------------------------------------------------------------------


def inv_identity_001(result_candidate_snapshot: str, evidence_candidate_snapshot: str) -> bool:
    """A VerificationResult.candidate_snapshot equals the exact CandidateSnapshot its evidence was produced against."""
    return result_candidate_snapshot == evidence_candidate_snapshot


def inv_identity_002(
    manifest_change_revision_id: str,
    governed_change_revision_id: str,
    manifest_candidate_snapshot: str,
    governed_candidate_snapshot: str,
) -> bool:
    """An EvidenceManifest's change_revision_id and candidate_snapshot match the currently governed values."""
    return manifest_change_revision_id == governed_change_revision_id and manifest_candidate_snapshot == governed_candidate_snapshot


# ---------------------------------------------------------------------------
# GOAL
# ---------------------------------------------------------------------------


def inv_goal_001(
    change_goal_revision_id: str,
    change_run_id: str,
    known_goal_revisions: set[tuple[str, str]],
) -> bool:
    """A ChangeContract must reference an existing Goal revision belonging to the same run.

    `known_goal_revisions` is the set of (goal_revision_id, run_id) pairs
    currently persisted for the run.
    """
    return (change_goal_revision_id, change_run_id) in known_goal_revisions


# ---------------------------------------------------------------------------
# REVISION
# ---------------------------------------------------------------------------


def inv_revision_001(bound_identity: str, current_identity: str) -> bool:
    """True if dependent state bound to `bound_identity` remains current-valid (identity unchanged).

    A material Goal/Change revision changes the identity; callers use the
    False result to remove approvals/plans/checks/reviews/evidence from the
    current-valid view without deleting their history rows.
    """
    return bound_identity == current_identity


# ---------------------------------------------------------------------------
# APPROVAL
# ---------------------------------------------------------------------------


def inv_approval_001(grant_request_digest: str, candidate_request_digest: str) -> bool:
    """A grant authorizes only the ApprovalRequest digest to which it is bound."""
    return grant_request_digest == candidate_request_digest


def inv_approval_002(
    previous: dict[str, Any],
    proposed: dict[str, Any],
    *,
    fields: tuple[str, ...] = (
        "effects",
        "resources",
        "argument_digest",
        "credential_exposure",
        "reversibility",
        "tool_schema_digest",
    ),
) -> bool:
    """True if `proposed` requires a brand-new ApprovalRequest relative to `previous`.

    Any change to effects, normalized resources, arguments, credential
    exposure, reversibility, or tool schema identity requires re-approval.
    """
    for field in fields:
        prev_value = previous.get(field)
        new_value = proposed.get(field)
        if field == "effects":
            # 9.6.3: effects is a set[Effect]; order is not semantic.
            if set(prev_value or []) != set(new_value or []):
                return True
        elif canonical_json_bytes(prev_value) != canonical_json_bytes(new_value):
            return True
    return False


# ---------------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------------

_CANONICAL_STATES: frozenset[str] = frozenset(
    {
        "CREATED", "REPOSITORY_READY", "GOAL_BOUND", "RECONNAISSANCE", "PLAN_READY",
        "IMPLEMENTING", "VERIFYING_FOCUSED", "VERIFYING_BROAD", "INTENT_REVIEW",
        "READY_FOR_USER", "ACCEPTING", "ACCEPTED", "REJECTED", "BLOCKED",
        "INTEGRATION_CONFLICT", "RECOVERY_REQUIRED", "RECONCILIATION_REQUIRED",
        "FAILED", "INTERRUPTED",
    }
)

_TERMINAL_STATES: frozenset[str] = frozenset({"ACCEPTED", "REJECTED", "FAILED"})

# PROVISIONAL, NOT AN AUTHORITATIVE SOURCE: `StateMachine v1` (Blueprint
# Contract 5, 9.8) is not yet materialized under contracts/ (only DomainSchemas
# v1 and CrossContractInvariantRegistry v1 are, as of this phase slice). The
# table below is a literal, unmodified transcription of Blueprint 9.8.3/9.8.4's
# own transition relation -- not an invented semantic choice -- included only
# so INV-STATE-001 (required by CrossContractInvariantRegistry v1) has an
# executable predicate to test against. When StateMachine v1 is implemented as
# its own contracts/state_machine.* source, THIS TABLE MUST BE DELETED and
# inv_state_001 rewired to consult that source instead, so the transition
# relation has exactly one machine-readable owner (Canonical Identity Rules).
# 9.8.3 canonical forward transitions: (from_state, command) -> to_state.
_FORWARD_TRANSITIONS: dict[tuple[str, str], str] = {
    ("CREATED", "bind_repository"): "REPOSITORY_READY",
    ("REPOSITORY_READY", "bind_goal"): "GOAL_BOUND",
    ("GOAL_BOUND", "begin_reconnaissance"): "RECONNAISSANCE",
    ("RECONNAISSANCE", "finalize_plan"): "PLAN_READY",
    ("PLAN_READY", "begin_implementation"): "IMPLEMENTING",
    ("IMPLEMENTING", "begin_focused_verification"): "VERIFYING_FOCUSED",
    ("VERIFYING_FOCUSED", "focused_passed"): "VERIFYING_BROAD",
    ("VERIFYING_FOCUSED", "repair"): "IMPLEMENTING",
    ("VERIFYING_BROAD", "broad_passed"): "INTENT_REVIEW",
    ("VERIFYING_BROAD", "repair"): "IMPLEMENTING",
    ("INTENT_REVIEW", "review_passed"): "READY_FOR_USER",
    ("INTENT_REVIEW", "repair"): "IMPLEMENTING",
    ("READY_FOR_USER", "accept"): "ACCEPTING",
    ("READY_FOR_USER", "reject"): "REJECTED",
    ("ACCEPTING", "integration_verified"): "ACCEPTED",
    ("ACCEPTING", "integration_conflict"): "INTEGRATION_CONFLICT",
    ("ACCEPTING", "destination_drift"): "RECONCILIATION_REQUIRED",
}

# 9.8.4: any nonterminal active state may transition to one of these via its own symbolic command.
_EXCEPTIONAL_COMMAND_TARGET: dict[str, str] = {
    "block": "BLOCKED",
    "interrupt": "INTERRUPTED",
    "require_recovery": "RECOVERY_REQUIRED",
    "require_reconciliation": "RECONCILIATION_REQUIRED",
    "fail": "FAILED",
}


def inv_state_001(from_state: str, command: str, to_state: str) -> bool:
    """Only StateMachine v1's canonical relation may authorize a transition.

    True iff (from_state, command) -> to_state is one of the canonical
    forward transitions (9.8.3) or, for a nonterminal from_state, one of the
    exceptional transitions (9.8.4).
    """
    if from_state not in _CANONICAL_STATES or to_state not in _CANONICAL_STATES:
        return False
    forward_target = _FORWARD_TRANSITIONS.get((from_state, command))
    if forward_target is not None:
        return forward_target == to_state
    exceptional_target = _EXCEPTIONAL_COMMAND_TARGET.get(command)
    if exceptional_target is not None and from_state not in _TERMINAL_STATES:
        return exceptional_target == to_state
    return False


def inv_state_002(
    mandatory_criterion_ids: set[str],
    criterion_evaluations: dict[str, str],
) -> bool:
    """READY_FOR_USER requires every mandatory criterion SATISFIED or validly WAIVED, none unresolved FAIL/ERROR/INCONCLUSIVE."""
    acceptable = {"SATISFIED", "WAIVED"}
    for criterion_id in mandatory_criterion_ids:
        if criterion_evaluations.get(criterion_id) not in acceptable:
            return False
    return True


# ---------------------------------------------------------------------------
# ACCEPT
# ---------------------------------------------------------------------------


def inv_accept_001(integration_status: str, post_integration_checks_passed: bool) -> bool:
    """ACCEPTED requires completed integration plus required post-integration verification passing."""
    return integration_status == "COMPLETED" and post_integration_checks_passed


# ---------------------------------------------------------------------------
# SECURITY
# ---------------------------------------------------------------------------


def inv_security_001(effective_authority: frozenset[str], *bounds: frozenset[str]) -> bool:
    """Effective authority is never broader than the intersection of all applicable higher-authority constraints."""
    if not bounds:
        return not effective_authority
    intersection = frozenset.intersection(*bounds)
    return effective_authority <= intersection


def inv_security_002(base_capabilities: frozenset[str], untrusted_claimed_capabilities: frozenset[str]) -> frozenset[str]:
    """Repository/tool/external/model-generated content cannot create new capabilities or expand policy.

    Returns the effective capability set, which MUST always equal
    `base_capabilities` regardless of what an untrusted source claims.
    """
    return base_capabilities


# ---------------------------------------------------------------------------
# RESOURCE
# ---------------------------------------------------------------------------


def inv_resource_001(ordered_steps: tuple[str, ...]) -> bool:
    """Resource authorization occurs after canonical normalization and strictly before the side effect."""
    return ordered_steps == ("NORMALIZE", "AUTHORIZE", "EFFECT")


# ---------------------------------------------------------------------------
# WORKTREE
# ---------------------------------------------------------------------------


def inv_worktree_001(run_worktree_identity: str, target_identity: str, user_original_checkout_identity: str) -> bool:
    """A mutating tool call for a governed run targets the run's isolated worktree, never the user's original checkout."""
    if target_identity == user_original_checkout_identity:
        return False
    return target_identity == run_worktree_identity


# ---------------------------------------------------------------------------
# EVENT
# ---------------------------------------------------------------------------


def inv_event_001(domain_mutation_committed: bool, event_committed: bool, same_transaction: bool) -> bool:
    """A committed authoritative domain mutation has a corresponding committed event in the same SQLite transaction."""
    if not domain_mutation_committed:
        return True
    return event_committed and same_transaction


def inv_event_002(sequence_numbers: list[int]) -> bool:
    """Event sequence numbers are strictly increasing per run with no duplicate committed sequence number."""
    return all(b > a for a, b in zip(sequence_numbers, sequence_numbers[1:]))


# ---------------------------------------------------------------------------
# TOOL
# ---------------------------------------------------------------------------


def inv_tool_001(atomicity_guarantee_met: bool, status: str) -> bool:
    """Tool result success cannot be emitted for a partially applied atomic operation."""
    if status == "SUCCESS":
        return atomicity_guarantee_met
    return True


# ---------------------------------------------------------------------------
# VERIFY
# ---------------------------------------------------------------------------


def inv_verify_001(mandatory: bool, runnable: bool, status: str) -> bool:
    """An unrunnable mandatory check cannot be represented as PASS."""
    if mandatory and not runnable:
        return status != "PASS"
    return True


def inv_verify_002(
    result_identity_dependencies: dict[str, str],
    current_identity_values: dict[str, str],
    *,
    candidate_independent: bool = False,
) -> bool:
    """True if verification evidence remains valid (current) rather than invalidated by a candidate mutation.

    `result_identity_dependencies` maps each declared identity_dependencies
    entry (10.15.7) to the value it was bound to; `current_identity_values`
    is the current value for each of those dependency kinds. A candidate
    mutation invalidates the evidence unless the check contract explicitly
    proves candidate-independence.
    """
    if candidate_independent:
        return True
    for dependency, bound_value in result_identity_dependencies.items():
        if current_identity_values.get(dependency) != bound_value:
            return False
    return True


# ---------------------------------------------------------------------------
# SECRET
# ---------------------------------------------------------------------------


def _iter_strings(value: Any) -> Any:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _iter_strings(item)


def inv_secret_001(payload: Any, secret_plaintext_values: frozenset[str]) -> bool:
    """True (satisfied) if none of `secret_plaintext_values` appear verbatim anywhere in `payload`.

    Applies to ordinary event payloads, JSONL projections, model
    transcripts, and persisted tool outputs.
    """
    if not secret_plaintext_values:
        return True
    for text in _iter_strings(payload):
        for secret in secret_plaintext_values:
            if secret and secret in text:
                return False
    return True


CHECKERS: dict[str, Any] = {
    "INV-IDENTITY-001": inv_identity_001,
    "INV-IDENTITY-002": inv_identity_002,
    "INV-GOAL-001": inv_goal_001,
    "INV-REVISION-001": inv_revision_001,
    "INV-APPROVAL-001": inv_approval_001,
    "INV-APPROVAL-002": inv_approval_002,
    "INV-STATE-001": inv_state_001,
    "INV-STATE-002": inv_state_002,
    "INV-ACCEPT-001": inv_accept_001,
    "INV-SECURITY-001": inv_security_001,
    "INV-SECURITY-002": inv_security_002,
    "INV-RESOURCE-001": inv_resource_001,
    "INV-WORKTREE-001": inv_worktree_001,
    "INV-EVENT-001": inv_event_001,
    "INV-EVENT-002": inv_event_002,
    "INV-TOOL-001": inv_tool_001,
    "INV-VERIFY-001": inv_verify_001,
    "INV-VERIFY-002": inv_verify_002,
    "INV-SECRET-001": inv_secret_001,
}
