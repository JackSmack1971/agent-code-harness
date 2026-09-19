"""Runtime authority for `StateMachine v1` + `RecoveryProtocol v1` (Blueprint 3.4, 9.8, 10.8).

`contracts/state_machine.yaml` (validated against `state_machine.schema.json`)
is the sole authoritative source for the canonical state registry, the
forward/exceptional transition relation, and the canonical recovery relation.
This module is the only code in the repository permitted to decide whether a
requested transition or resume is authorized (INV-STATE-001: "Only
StateMachine v1 may authorize a runtime-state transition"); nothing here
hand-maintains a second copy of that relation.

Every function is pure: given the caller-supplied facts (current persisted
state/run_version, the request, and pre-evaluated guard/condition booleans),
each returns a decision without performing I/O, persistence, or side
effects. Full runtime wiring (SQLite persistence, live guard evaluation,
event journaling) belongs to Phase 1/8 components that do not exist yet,
exactly the same phase boundary `_invariants.py` and `_domain_schemas.py`
already document. Callers may repeatedly call `authorize_resume` with an
unchanged unsatisfied-condition snapshot and get back the identical
rejection every time (10.8.3 resume idempotency): the purity of this module
is what makes that idempotency true by construction, not an extra check.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from ._contracts import find_contracts_root, load_json, load_yaml

REASON_STATE_INVALID_TRANSITION = "STATE_INVALID_TRANSITION"
REASON_STATE_STALE_RUN_VERSION = "STATE_STALE_RUN_VERSION"
REASON_INTERNAL_INVARIANT_VIOLATION = "INTERNAL_INVARIANT_VIOLATION"

RECOVERABLE_SOURCE_STATES: frozenset[str] = frozenset(
    {"BLOCKED", "INTERRUPTED", "RECOVERY_REQUIRED", "RECONCILIATION_REQUIRED", "INTEGRATION_CONFLICT"}
)


class StateMachineError(ValueError):
    """The contract itself, or a caller-supplied request, is structurally invalid.

    Raised only for malformed input/contract shape -- never for an ordinary
    domain-level transition rejection, which is represented by
    `TransitionRejected`/`ResumeRejected` return values instead (9.8.2: a
    rejected transition does not mutate state, it is not an exception).
    """

    def __init__(self, message: str, *, reason_code: str = REASON_STATE_INVALID_TRANSITION) -> None:
        super().__init__(message)
        self.reason_code = reason_code


@dataclass(frozen=True)
class _ContractBundle:
    doc: dict[str, Any]
    registry: Registry


def _load_bundle(contracts_root: Path | None = None) -> _ContractBundle:
    root = contracts_root or find_contracts_root()
    if root is None:
        raise StateMachineError(
            "contracts/ root not found; cannot authorize a transition without the authoritative StateMachine v1 source"
        )
    return _load_bundle_cached(root)


@lru_cache(maxsize=8)
def _load_bundle_cached(root: Path) -> _ContractBundle:
    # Cached per resolved contracts_root: this process treats contracts/ as
    # read-only for its lifetime (same assumption `find_contracts_root()`'s
    # callers already make), so re-parsing/re-validating identical bytes on
    # every `is_valid_transition`/`authorize_transition` call is pure waste,
    # not additional correctness.
    schema_doc = load_json(root / "state_machine.schema.json")
    semantic_doc = load_json(root / "semantic_types.schema.json")
    data_doc = load_yaml(root / "state_machine.yaml")

    registry = Registry().with_resources(
        [
            (semantic_doc["$id"], Resource.from_contents(semantic_doc)),
            (schema_doc["$id"], Resource.from_contents(schema_doc)),
        ]
    )
    validator = Draft202012Validator(schema_doc, registry=registry)
    errors = sorted(validator.iter_errors(data_doc), key=str)
    if errors:
        raise StateMachineError(
            f"contracts/state_machine.yaml failed StateMachine v1 validation: {[e.message for e in errors]}"
        )
    return _ContractBundle(doc=data_doc, registry=registry)


def load_state_machine(contracts_root: Path | None = None) -> dict[str, Any]:
    """Return the validated `StateMachine v1` + `RecoveryProtocol v1` data document."""
    return _load_bundle(contracts_root).doc


def _forward_target(doc: dict[str, Any], from_state: str, command: str) -> str | None:
    for row in doc["forward_transitions"]:
        if row["from"] == from_state and row["command"] == command:
            return row["to"]
    return None


def _forward_row(doc: dict[str, Any], from_state: str, command: str) -> dict[str, Any] | None:
    for row in doc["forward_transitions"]:
        if row["from"] == from_state and row["command"] == command:
            return row
    return None


def _exceptional_target(doc: dict[str, Any], command: str) -> str | None:
    for entry in doc["exceptional_transitions"]["entries"]:
        if entry["command"] == command:
            return entry["to"]
    return None


def is_valid_transition(from_state: str, command: str, to_state: str, *, contracts_root: Path | None = None) -> bool:
    """True iff (from_state, command) -> to_state is authorized by the canonical relation.

    This is the sole executable predicate behind INV-STATE-001; it consults
    `contracts/state_machine.yaml` rather than a hand-maintained copy.
    """
    doc = load_state_machine(contracts_root)
    states = set(doc["states"])
    terminal = set(doc["terminal_states"])
    if from_state not in states or to_state not in states:
        return False

    forward_target = _forward_target(doc, from_state, command)
    if forward_target is not None:
        return forward_target == to_state

    if from_state in terminal:
        return False
    exceptional_target = _exceptional_target(doc, command)
    if exceptional_target is not None:
        return exceptional_target == to_state
    return False


# ---------------------------------------------------------------------------
# Forward/exceptional transition authorization (9.8.2, 9.8.5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitionCommitted:
    from_state: str
    to_state: str
    command: str
    new_run_version: int
    invalidation_rule: str | None
    checkpoint_persisted: bool = True


@dataclass(frozen=True)
class TransitionRejected:
    reason_code: str
    detail: str


TransitionResult = TransitionCommitted | TransitionRejected


# Commands whose target is a hard-gated state (9.15.7 READY_FOR_USER Gate,
# 9.15.8 ACCEPTED Gate). `authorize_transition` refuses to commit these
# without caller-supplied guard evidence, evaluated through the existing
# INV-STATE-002 / INV-ACCEPT-001 checkers -- the same checkers
# CrossContractInvariantRegistry v1 already names as their authoritative
# predicate -- so the gate cannot be bypassed by a caller simply omitting
# evidence. Missing evidence fails closed (treated as guard-not-satisfied).
_READY_FOR_USER_COMMAND = "review_passed"
_ACCEPTED_COMMAND = "integration_verified"


def _guard_satisfied(command: str, guard_context: Mapping[str, Any] | None) -> tuple[bool, str]:
    if command == _READY_FOR_USER_COMMAND:
        from ._invariants import inv_state_002

        if guard_context is None or "mandatory_criterion_ids" not in guard_context or "criterion_evaluations" not in guard_context:
            return False, "READY_FOR_USER guard (INV-STATE-002) requires mandatory_criterion_ids/criterion_evaluations evidence"
        ok = inv_state_002(guard_context["mandatory_criterion_ids"], guard_context["criterion_evaluations"])
        return ok, "" if ok else "READY_FOR_USER guard (INV-STATE-002) not satisfied"

    if command == _ACCEPTED_COMMAND:
        from ._invariants import inv_accept_001

        if guard_context is None or "integration_status" not in guard_context or "post_integration_checks_passed" not in guard_context:
            return False, "ACCEPTED guard (INV-ACCEPT-001) requires integration_status/post_integration_checks_passed evidence"
        ok = inv_accept_001(guard_context["integration_status"], guard_context["post_integration_checks_passed"])
        return ok, "" if ok else "ACCEPTED guard (INV-ACCEPT-001) not satisfied"

    return True, ""


def authorize_transition(
    request: Mapping[str, Any],
    *,
    current_state: str,
    current_run_version: int,
    guard_context: Mapping[str, Any] | None = None,
    contracts_root: Path | None = None,
) -> TransitionResult:
    """Decide a `TransitionCommand` (9.8.2) against live (current_state, current_run_version).

    Never mutates anything -- callers apply `TransitionCommitted`'s four
    canonical effects (9.8.5) themselves. Optimistic concurrency is checked
    before the transition relation: a stale `expected_run_version` is
    rejected with STATE_STALE_RUN_VERSION regardless of whether the
    requested transition would otherwise be valid. `review_passed`
    (-> READY_FOR_USER) and `integration_verified` (-> ACCEPTED) additionally
    require `guard_context` evidence (see `_guard_satisfied`); without it the
    transition is rejected rather than committed.
    """
    bundle = _load_bundle(contracts_root)
    doc = bundle.doc
    validator = Draft202012Validator({"$ref": f"{doc['$schema']}#/$defs/TransitionCommand"}, registry=bundle.registry)
    errors = sorted(validator.iter_errors(dict(request)), key=str)
    if errors:
        raise StateMachineError(f"malformed TransitionCommand: {[e.message for e in errors]}")

    if request["expected_run_version"] != current_run_version:
        return TransitionRejected(
            reason_code=REASON_STATE_STALE_RUN_VERSION,
            detail=f"expected_run_version {request['expected_run_version']} != current {current_run_version}",
        )

    from_state = request["from_state"]
    to_state = request["to_state"]
    command = request["command"]

    if from_state != current_state:
        return TransitionRejected(
            reason_code=REASON_STATE_INVALID_TRANSITION,
            detail=f"request.from_state {from_state!r} != current_state {current_state!r}",
        )

    if not is_valid_transition(from_state, command, to_state, contracts_root=contracts_root):
        return TransitionRejected(
            reason_code=REASON_STATE_INVALID_TRANSITION,
            detail=f"({from_state}, {command}) -> {to_state} is not a canonical transition",
        )

    guard_ok, guard_detail = _guard_satisfied(command, guard_context)
    if not guard_ok:
        return TransitionRejected(reason_code=REASON_STATE_INVALID_TRANSITION, detail=guard_detail)

    row = _forward_row(doc, from_state, command)
    invalidation_rule = row.get("invalidation_rule") if row is not None else None
    return TransitionCommitted(
        from_state=from_state,
        to_state=to_state,
        command=command,
        new_run_version=current_run_version + 1,
        invalidation_rule=invalidation_rule,
    )


# ---------------------------------------------------------------------------
# Recovery relation / resume authorization (10.8)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResumeCommitted:
    from_state: str
    to_state: str
    command: str
    new_run_version: int
    checkpoint_persisted: bool = True


@dataclass(frozen=True)
class ResumeRejected:
    reason_code: str
    detail: str
    blocker_reason_code: str | None = None


ResumeResult = ResumeCommitted | ResumeRejected


def _recovery_relation(doc: dict[str, Any], source_state: str) -> dict[str, Any] | None:
    for relation in doc["recovery_transitions"]:
        if relation["source_state"] == source_state:
            return relation
    return None


def authorize_resume(
    *,
    current_state: str,
    current_run_version: int,
    expected_run_version: int,
    resume_target_state: str | None = None,
    last_safe_checkpoint_state: str | None = None,
    disposition: str | None = None,
    conditions_satisfied: Mapping[str, bool] | None = None,
    blocker_reason_code: str = "RECOVERY_EXTERNAL_DRIFT",
    contracts_root: Path | None = None,
) -> ResumeResult:
    """Decide a `resume` (or INTEGRATION_CONFLICT disposition) request against the recovery relation.

    Idempotent by construction (10.8.3): called again with the same
    `current_state`/`conditions_satisfied`/`blocker_reason_code` snapshot,
    this pure function returns an identical `ResumeRejected` carrying the
    same `blocker_reason_code`, and performs no mutation or side effect
    either time.
    """
    conditions_satisfied = conditions_satisfied or {}

    if expected_run_version != current_run_version:
        return ResumeRejected(
            reason_code=REASON_STATE_STALE_RUN_VERSION,
            detail=f"expected_run_version {expected_run_version} != current {current_run_version}",
        )

    if current_state not in RECOVERABLE_SOURCE_STATES:
        # 10.8.3: "Calling resume when the run is already active is STATE_INVALID_TRANSITION."
        return ResumeRejected(
            reason_code=REASON_STATE_INVALID_TRANSITION,
            detail=f"{current_state} is not a recoverable source_state; run is already active",
        )

    doc = load_state_machine(contracts_root)
    relation = _recovery_relation(doc, current_state)
    if relation is None:
        raise StateMachineError(
            f"contracts/state_machine.yaml has no recovery_transitions entry for {current_state!r}"
        )

    target_mode = relation["target_mode"]
    if target_mode == "FIXED_BY_DISPOSITION":
        branch = next((b for b in relation["branches"] if b["disposition"] == disposition), None)
        if branch is None:
            return ResumeRejected(
                reason_code=REASON_STATE_INVALID_TRANSITION,
                detail=f"disposition {disposition!r} is not one of {[b['disposition'] for b in relation['branches']]}",
            )
        target_state = branch["to"]
        command = branch["command"]
    else:
        target_state = resume_target_state if target_mode == "RESUME_TARGET_STATE" else last_safe_checkpoint_state
        command = relation["command"]
        if target_state is None:
            return ResumeRejected(
                reason_code=REASON_STATE_INVALID_TRANSITION,
                detail=f"{current_state} has no persisted {target_mode.lower()} to resume to",
                blocker_reason_code=blocker_reason_code,
            )

    if target_state == "ACCEPTED":
        # 10.8.2: "No recovery transition may target ACCEPTED directly." Defended at
        # runtime too, not only by contract-data validation, since RESUME_TARGET_STATE
        # and LAST_SAFE_CHECKPOINT are dynamic values a caller supplies.
        raise StateMachineError(
            f"recovery target for {current_state} resolved to ACCEPTED; refusing to authorize",
            reason_code=REASON_INTERNAL_INVARIANT_VIOLATION,
        )

    unmet = [cond for cond in relation["required_conditions"] if not conditions_satisfied.get(cond, False)]
    if unmet:
        return ResumeRejected(
            reason_code="RECOVERY_EXTERNAL_DRIFT",
            detail=f"unmet required_conditions: {unmet}",
            blocker_reason_code=blocker_reason_code,
        )

    return ResumeCommitted(
        from_state=current_state,
        to_state=target_state,
        command=command,
        new_run_version=current_run_version + 1,
    )
