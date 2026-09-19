"""Deterministic VerificationProtocol v1 evaluation and check execution.

This module is deliberately separate from orchestration.  It accepts already
validated contract-shaped values, evaluates evidence algebra, and never lets a
missing or stale observation become a successful gate.
"""

from __future__ import annotations

import importlib
import json
import re
import subprocess
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from ._canonical import digest_for
from ._invariants import inv_verify_002
from ._semantic_validation import validate_evidence_requirement

CLAIM_ESTABLISHED = "ESTABLISHED"
CLAIM_DISPROVEN = "DISPROVEN"
CLAIM_INCONCLUSIVE = "INCONCLUSIVE"
CLAIM_WAIVED = "WAIVED"

CHECK_PASS = "PASS"
CHECK_FAIL = "FAIL"
CHECK_ERROR = "ERROR"
CHECK_INCONCLUSIVE = "INCONCLUSIVE"
CHECK_NOT_APPLICABLE = "NOT_APPLICABLE"

REASON_VERIFY_FAILED = "VERIFY_FAILED"
REASON_VERIFY_INCONCLUSIVE = "VERIFY_INCONCLUSIVE"
REASON_VERIFY_STALE = "VERIFY_STALE_EVIDENCE"
REASON_VERIFY_REVIEWER_UNAVAILABLE = "VERIFY_REVIEWER_UNAVAILABLE"
REASON_VERIFY_INVALID_MECHANISM = "VERIFY_INVALID_MECHANISM"

MECHANISM_KINDS = frozenset(
    {"COMMAND", "PYTHON_CALLABLE", "JSON_ASSERTION", "FILE_ASSERTION", "REPOSITORY_INVARIANT", "ARTIFACT_COMPARISON", "REVIEWER"}
)


@dataclass(frozen=True)
class ClaimEvaluation:
    claim_id: str
    state: str
    evidence_refs: tuple[str, ...] = ()
    reason_code: str | None = None


@dataclass(frozen=True)
class CriterionEvaluation:
    criterion_id: str
    evaluation: str
    claim_states: Mapping[str, str]
    reason_code: str | None = None


@dataclass(frozen=True)
class CheckExecution:
    status: str
    reason_code: str | None = None
    stdout: str = ""
    stderr: str = ""
    detail: str | None = None


def _kind_for_ref(ref: Mapping[str, Any]) -> str:
    return {
        "VERIFICATION_RESULT": "CHECK_RESULT",
        "REVIEW_RESULT": "REVIEW",
        "ARTIFACT": "ARTIFACT",
        "REPOSITORY_FACT": "REPOSITORY_FACT",
        "WAIVER": "CHECK_RESULT",
    }.get(str(ref.get("kind")), "")


def result_is_current(
    check: Mapping[str, Any],
    result: Mapping[str, Any],
    current_identities: Mapping[str, str],
    *,
    candidate_snapshot: str | None = None,
    candidate_independent: bool = False,
) -> bool:
    """Return whether a result is valid for the exact current identity set."""
    if result.get("status") not in {CHECK_PASS, CHECK_FAIL, CHECK_ERROR, CHECK_INCONCLUSIVE, CHECK_NOT_APPLICABLE}:
        return False
    if candidate_snapshot is not None and not candidate_independent and result.get("candidate_snapshot") != candidate_snapshot:
        return False
    dependencies = check.get("identity_dependencies", [])
    bound = result.get("identity_dependencies") or result.get("bound_identities") or {}
    if "CANDIDATE_SNAPSHOT" in dependencies and candidate_snapshot is not None and not candidate_independent:
        if result.get("candidate_snapshot") != candidate_snapshot:
            return False
    if not isinstance(bound, Mapping):
        return False if dependencies else True
    dependencies = [dependency for dependency in dependencies if not (candidate_independent and dependency == "CANDIDATE_SNAPSHOT")]
    if any(dependency not in bound or dependency not in current_identities for dependency in dependencies):
        return False
    return inv_verify_002(
        {str(k): str(bound[k]) for k in dependencies},
        {str(k): str(current_identities[k]) for k in dependencies},
        candidate_independent=False,
    )


def evaluate_claim(
    claim: Mapping[str, Any],
    *,
    results: Mapping[str, Mapping[str, Any]] | None = None,
    evidence: list[Mapping[str, Any]] | None = None,
    waivers: list[Mapping[str, Any]] | None = None,
    checks: Mapping[str, Mapping[str, Any]] | None = None,
    current_identities: Mapping[str, str] | None = None,
    candidate_snapshot: str | None = None,
) -> ClaimEvaluation:
    """Evaluate one claim using only permitted, current evidence paths."""
    results = results or {}
    evidence = evidence or []
    waivers = waivers or []
    checks = checks or {}
    current_identities = current_identities or {}
    claim_id = str(claim["claim_id"])
    required = set(claim.get("required_evidence_kinds", []))
    matched: list[str] = []
    disproven = False
    inconclusive = False
    for result in results.values():
        if claim_id not in result.get("claim_refs", []):
            continue
        check = checks.get(str(result.get("check_id")), {})
        if not result_is_current(check, result, current_identities, candidate_snapshot=candidate_snapshot):
            inconclusive = True
            continue
        kind = "CHECK_RESULT"
        if kind not in required:
            continue
        if result.get("status") == CHECK_FAIL:
            disproven = True
        elif result.get("status") == CHECK_PASS:
            matched.append(str(result.get("digest", result.get("check_id", ""))))
        else:
            inconclusive = True
    for ref in evidence:
        if ref.get("claim_id") == claim_id and _kind_for_ref(ref) in required:
            matched.append(str(ref.get("digest", "")))
    for waiver in waivers:
        if waiver.get("scope_ref") not in {claim_id, *[str(x) for x in claim.get("criterion_refs", [])]}:
            continue
        if candidate_snapshot is not None and waiver.get("bound_candidate") not in (None, candidate_snapshot):
            continue
        expires = waiver.get("expires_at")
        if expires:
            try:
                if dt.datetime.fromisoformat(str(expires).replace("Z", "+00:00")) <= dt.datetime.now(dt.timezone.utc):
                    continue
            except ValueError:
                continue
        if waiver.get("issued_by") not in {"USER", "TRUSTED_CI"} or not waiver.get("policy_rule_id"):
            continue
        return ClaimEvaluation(claim_id, CLAIM_WAIVED, tuple(matched), "VERIFY_WAIVER_REQUIRED")
    if disproven:
        return ClaimEvaluation(claim_id, CLAIM_DISPROVEN, tuple(matched), REASON_VERIFY_FAILED)
    if matched and required and "CHECK_RESULT" in required:
        return ClaimEvaluation(claim_id, CLAIM_ESTABLISHED, tuple(matched))
    if inconclusive or not matched:
        return ClaimEvaluation(claim_id, CLAIM_INCONCLUSIVE, tuple(matched), REASON_VERIFY_INCONCLUSIVE)
    return ClaimEvaluation(claim_id, CLAIM_ESTABLISHED, tuple(matched))


def evaluate_criterion(
    criterion: Mapping[str, Any], claims: Mapping[str, ClaimEvaluation],
) -> CriterionEvaluation:
    requirement = criterion["success_semantics"]
    validate_evidence_requirement(requirement["mode"], list(requirement["claim_refs"]), requirement.get("threshold"))
    states = {ref: claims.get(ref, ClaimEvaluation(ref, CLAIM_INCONCLUSIVE)).state for ref in requirement["claim_refs"]}
    established = sum(state == CLAIM_ESTABLISHED for state in states.values())
    waived = sum(state == CLAIM_WAIVED for state in states.values())
    disproven = any(state == CLAIM_DISPROVEN for state in states.values())
    mode = requirement["mode"]
    if disproven:
        evaluation = "UNSATISFIED"
    elif mode == "ALL":
        evaluation = "SATISFIED" if established + waived == len(states) else "INCONCLUSIVE"
    elif mode == "ANY":
        evaluation = "SATISFIED" if established else ("WAIVED" if requirement.get("allow_waiver") and waived == len(states) else "INCONCLUSIVE")
    else:
        evaluation = "SATISFIED" if established + (waived if requirement.get("allow_waiver") else 0) >= int(requirement["threshold"]) else "INCONCLUSIVE"
    return CriterionEvaluation(str(criterion["criterion_id"]), evaluation, states, REASON_VERIFY_FAILED if evaluation == "UNSATISFIED" else None)


def evaluate_ready_for_user(
    criteria: list[Mapping[str, Any]], evaluations: Mapping[str, CriterionEvaluation],
    *, candidate_snapshot: str | None, manifest_candidate_snapshot: str | None,
    intent_review_status: str | Mapping[str, Any] | None, manifest_digest: str | None,
) -> bool:
    """Evaluate the complete READY_FOR_USER gate, without orchestration shortcuts."""
    if not candidate_snapshot or candidate_snapshot != manifest_candidate_snapshot or not manifest_digest:
        return False
    if isinstance(intent_review_status, Mapping):
        review = evaluate_intent_review(intent_review_status, candidate_snapshot=candidate_snapshot, required_criterion_ids={str(c["criterion_id"]) for c in criteria if c.get("mandatory", True)})
        if review.status != CHECK_PASS:
            return False
    elif intent_review_status != "PASS":
        return False
    return all(evaluations.get(str(c["criterion_id"]), CriterionEvaluation("", "INCONCLUSIVE", {})).evaluation in {"SATISFIED", "WAIVED"} for c in criteria if c.get("mandatory", True))


def evaluate_accepted(*, destination_reconciled: bool, integration_status: str, landed_destination_identity: str | None, post_integration: list[str]) -> bool:
    return bool(destination_reconciled and integration_status == "COMPLETED" and landed_destination_identity and post_integration and all(status in {CHECK_PASS, CHECK_NOT_APPLICABLE} for status in post_integration))


def evaluate_intent_review(
    review: Mapping[str, Any], *, candidate_snapshot: str | None,
    required_criterion_ids: set[str], reviewer_available: bool = True,
    required_route: str | None = None, implementer_context_digest: str | None = None,
) -> CheckExecution:
    """Evaluate independent intent-review evidence without trusting narration."""
    if not reviewer_available:
        return CheckExecution(CHECK_INCONCLUSIVE, REASON_VERIFY_REVIEWER_UNAVAILABLE)
    if review.get("overall_status") != "PASS":
        return CheckExecution(CHECK_FAIL, REASON_VERIFY_FAILED)
    if candidate_snapshot is None or review.get("candidate_snapshot") != candidate_snapshot:
        return CheckExecution(CHECK_INCONCLUSIVE, REASON_VERIFY_STALE)
    if required_route is not None and review.get("reviewer_route") != required_route:
        return CheckExecution(CHECK_FAIL, REASON_VERIFY_FAILED)
    context_digest = review.get("independence_context_digest")
    if not context_digest or (implementer_context_digest is not None and context_digest == implementer_context_digest):
        return CheckExecution(CHECK_INCONCLUSIVE, REASON_VERIFY_REVIEWER_UNAVAILABLE)
    criterion_results = {str(item.get("criterion_id")): item.get("status") for item in review.get("criterion_results", [])}
    if set(criterion_results) != required_criterion_ids or any(criterion_results.get(item) != "PASS" for item in required_criterion_ids):
        return CheckExecution(CHECK_FAIL, REASON_VERIFY_FAILED)
    return CheckExecution(CHECK_PASS)


def post_integration_reuse_allowed(check: Mapping[str, Any], *, candidate_tree_digest: str, landed_tree_digest: str) -> bool:
    """Apply the narrow pre-integration evidence reuse rule from 10.15.8."""
    dependencies = set(check.get("identity_dependencies", []))
    if check.get("check_type") == "POST_INTEGRATION":
        return False
    if dependencies & {"DESTINATION_SNAPSHOT", "ENVIRONMENT_DIGEST"}:
        return False
    return candidate_tree_digest == landed_tree_digest


def validate_mechanism(mechanism: Mapping[str, Any]) -> None:
    kind = mechanism.get("kind")
    if kind not in MECHANISM_KINDS:
        raise ValueError(f"{REASON_VERIFY_INVALID_MECHANISM}: unsupported mechanism {kind!r}")
    if kind == "COMMAND" and (not isinstance(mechanism.get("argv"), list) or not mechanism["argv"] or not all(isinstance(x, str) and x for x in mechanism["argv"])):
        raise ValueError(f"{REASON_VERIFY_INVALID_MECHANISM}: COMMAND requires a non-empty argv")
    if kind == "PYTHON_CALLABLE" and not isinstance(mechanism.get("callable_ref"), str):
        raise ValueError(f"{REASON_VERIFY_INVALID_MECHANISM}: PYTHON_CALLABLE requires callable_ref")


def _json_pointer(value: Any, pointer: str) -> tuple[bool, Any]:
    if pointer == "":
        return True, value
    if not pointer.startswith("/"):
        return False, None
    current = value
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        elif isinstance(current, dict) and token in current:
            current = current[token]
        else:
            return False, None
    return True, current


def _compare(actual: Any, comparator: str, expected: Any = None) -> bool:
    if comparator == "exists": return actual is not None
    if comparator == "equals": return actual == expected
    if comparator == "not_equals": return actual != expected
    if comparator == "contains": return expected in actual
    if comparator == "gt": return actual > expected
    if comparator == "gte": return actual >= expected
    if comparator == "lt": return actual < expected
    if comparator == "lte": return actual <= expected
    return False


def execute_check(check: Mapping[str, Any], *, cwd: Path | None = None, artifacts: Mapping[str, Any] | None = None, invariant_registry: Mapping[str, Callable[..., bool]] | None = None, reviewer_available: bool = False) -> CheckExecution:
    """Execute one typed check.  Unknown/unrunnable required checks never PASS."""
    try:
        validate_mechanism(check["mechanism"])
        mechanism = check["mechanism"]
        applicability = check.get("applicability")
        if applicability is not None and not evaluate_applicability(applicability, cwd=cwd, context=artifacts or {}):
            return CheckExecution(CHECK_NOT_APPLICABLE)
        kind = mechanism["kind"]
        if kind == "REVIEWER" and not reviewer_available:
            return CheckExecution(CHECK_INCONCLUSIVE, REASON_VERIFY_REVIEWER_UNAVAILABLE)
        if kind == "COMMAND":
            proc = subprocess.run(mechanism["argv"], cwd=cwd, capture_output=True, text=True, timeout=check.get("timeout_ms", 0) / 1000 or None, check=False)
            expected = set(mechanism.get("expected_exit_codes", [0]))
            predicate = check.get("success_predicate", {"kind": "EXIT_CODE_SET", "exit_codes": list(expected)})
            ok = proc.returncode in set(predicate.get("exit_codes", expected))
            if predicate.get("kind") == "REGEX_MATCH":
                ok = bool(re.search(predicate["pattern"], proc.stdout if predicate["target"] == "STDOUT" else proc.stderr))
            for assertion, stream in [(item, proc.stdout) for item in mechanism.get("stdout_assertions", [])] + [(item, proc.stderr) for item in mechanism.get("stderr_assertions", [])]:
                value = assertion.get("value", "")
                assertion_ok = (value in stream if assertion["kind"] == "CONTAINS" else value not in stream if assertion["kind"] == "NOT_CONTAINS" else bool(re.search(value, stream)) if assertion["kind"] == "REGEX_MATCH" else len(stream) <= int(value))
                ok = ok and assertion_ok
            return CheckExecution(CHECK_PASS if ok else CHECK_FAIL, None if ok else REASON_VERIFY_FAILED, proc.stdout, proc.stderr)
        if kind == "PYTHON_CALLABLE":
            module_name, attr = mechanism["callable_ref"].split(":", 1)
            value = getattr(importlib.import_module(module_name), attr)()
            return CheckExecution(CHECK_PASS if bool(value) else CHECK_FAIL, None if bool(value) else REASON_VERIFY_FAILED)
        if kind == "REPOSITORY_INVARIANT":
            ok = bool((invariant_registry or {})[mechanism["invariant_id"]]())
            return CheckExecution(CHECK_PASS if ok else CHECK_FAIL, None if ok else REASON_VERIFY_FAILED)
        if kind == "REVIEWER":
            return CheckExecution(CHECK_PASS)
        data = (artifacts or {}).get(mechanism.get("target_artifact_id"))
        if kind == "JSON_ASSERTION":
            found, actual = _json_pointer(data, mechanism["json_pointer"])
            assertion_ok = found if mechanism["comparator"] == "exists" else found and _compare(actual, mechanism["comparator"], mechanism.get("expected"))
            return CheckExecution(CHECK_PASS if assertion_ok else CHECK_FAIL, None if assertion_ok else REASON_VERIFY_FAILED)
        if kind == "ARTIFACT_COMPARISON":
            left, right = ((artifacts or {}).get(mechanism[k]) for k in ("baseline_artifact_id", "candidate_artifact_id"))
            ok = left == right if mechanism["comparator"] == "BYTE_EQUAL" else digest_for(left) == digest_for(right)
            return CheckExecution(CHECK_PASS if ok else CHECK_FAIL, None if ok else REASON_VERIFY_FAILED)
        if kind == "FILE_ASSERTION":
            path = (cwd or Path.cwd()) / mechanism["path"]
            exists = path.exists()
            assertion = mechanism["assertion"]
            if assertion == "EXISTS":
                ok = exists
            elif assertion == "NOT_EXISTS":
                ok = not exists
            elif assertion == "CONTAINS":
                ok = exists and str(mechanism.get("expected", "")) in path.read_text(encoding="utf-8")
            elif assertion == "DIGEST_EQUALS":
                ok = exists and digest_for(path.read_bytes()) == mechanism.get("expected")
            else:
                ok = False
            return CheckExecution(CHECK_PASS if ok else CHECK_FAIL, None if ok else REASON_VERIFY_FAILED)
        return CheckExecution(CHECK_INCONCLUSIVE, REASON_VERIFY_INCONCLUSIVE)
    except ValueError as exc:
        reason = REASON_VERIFY_INVALID_MECHANISM if str(exc).startswith(REASON_VERIFY_INVALID_MECHANISM) else REASON_VERIFY_INCONCLUSIVE
        return CheckExecution(CHECK_ERROR, reason, detail=str(exc))
    except (subprocess.TimeoutExpired, KeyError, ImportError, AttributeError, OSError, json.JSONDecodeError) as exc:
        return CheckExecution(CHECK_ERROR, REASON_VERIFY_INCONCLUSIVE, detail=str(exc))


def evaluate_applicability(rule: Mapping[str, Any], *, cwd: Path | None = None, context: Mapping[str, Any] | None = None) -> bool:
    """Evaluate the closed, deterministic applicability vocabulary."""
    kind = rule.get("kind")
    if kind == "ALWAYS":
        return True
    if kind == "NEVER":
        return False
    if kind == "FILE_EXISTS":
        return ((cwd or Path.cwd()) / str(rule["path"])).exists()
    if kind == "CONTEXT_EQUALS":
        return (context or {}).get(rule.get("key")) == rule.get("value")
    raise ValueError(f"{REASON_VERIFY_INVALID_MECHANISM}: unknown applicability rule {kind!r}")
