from __future__ import annotations

from pathlib import Path

from agentic_harness._verification import (
    CLAIM_ESTABLISHED,
    CHECK_INCONCLUSIVE,
    CHECK_PASS,
    evaluate_accepted,
    evaluate_applicability,
    evaluate_criterion,
    execute_check,
    post_integration_reuse_allowed,
    evaluate_intent_review,
    result_is_current,
)


def _criterion(mode: str, refs: list[str], *, threshold: int | None = None, allow_waiver: bool = False) -> dict:
    return {"criterion_id": "c", "success_semantics": {"mode": mode, "claim_refs": refs, "threshold": threshold, "allow_waiver": allow_waiver}}


def test_evidence_algebra_is_deterministic_and_waivers_do_not_create_any_success() -> None:
    claims = {"a": type("Claim", (), {"state": CLAIM_ESTABLISHED})(), "b": type("Claim", (), {"state": "WAIVED"})()}
    assert evaluate_criterion(_criterion("ALL", ["a", "b"]), claims).evaluation == "SATISFIED"
    assert evaluate_criterion(_criterion("ANY", ["b", "missing"]), claims).evaluation == "INCONCLUSIVE"


def test_stale_declared_identity_invalidates_evidence() -> None:
    check = {"identity_dependencies": ["CANDIDATE_SNAPSHOT", "CONFIG_DIGEST"]}
    result = {"status": CHECK_PASS, "candidate_snapshot": "sha256:new", "identity_dependencies": {"CANDIDATE_SNAPSHOT": "sha256:new", "CONFIG_DIGEST": "sha256:old"}}
    assert not result_is_current(check, result, {"CANDIDATE_SNAPSHOT": "sha256:new", "CONFIG_DIGEST": "sha256:current"}, candidate_snapshot="sha256:new")


def test_unavailable_reviewer_is_inconclusive() -> None:
    result = execute_check({"mechanism": {"kind": "REVIEWER", "reviewer_route": "reviewer"}, "identity_dependencies": []})
    assert result.status == CHECK_INCONCLUSIVE


def test_applicability_is_deterministic() -> None:
    assert evaluate_applicability({"kind": "NEVER"}) is False
    assert evaluate_applicability({"kind": "CONTEXT_EQUALS", "key": "mode", "value": "ci"}, context={"mode": "ci"}) is True


def test_accepted_requires_landed_identity_and_post_integration_passes() -> None:
    assert evaluate_accepted(destination_reconciled=True, integration_status="COMPLETED", landed_destination_identity="sha1:x", post_integration=["PASS"])
    assert not evaluate_accepted(destination_reconciled=True, integration_status="COMPLETED", landed_destination_identity=None, post_integration=["PASS"])


def test_post_integration_reuse_requires_exact_landed_tree_and_safe_dependencies() -> None:
    check = {"check_type": "FOCUSED", "identity_dependencies": ["CANDIDATE_SNAPSHOT"]}
    assert post_integration_reuse_allowed(check, candidate_tree_digest="sha256:x", landed_tree_digest="sha256:x")
    assert not post_integration_reuse_allowed({"check_type": "FOCUSED", "identity_dependencies": ["DESTINATION_SNAPSHOT"]}, candidate_tree_digest="sha256:x", landed_tree_digest="sha256:x")


def test_intent_review_requires_fresh_independent_context_and_exact_candidate() -> None:
    review = {"overall_status": "PASS", "candidate_snapshot": "sha256:c", "reviewer_route": "reviewer", "reviewer_model_identity": "m", "independence_context_digest": "sha256:review", "criterion_results": [{"criterion_id": "c", "status": "PASS"}]}
    assert evaluate_intent_review(review, candidate_snapshot="sha256:c", required_criterion_ids={"c"}).status == CHECK_PASS
    assert evaluate_intent_review(review, candidate_snapshot="sha256:c", required_criterion_ids={"c"}, implementer_context_digest="sha256:review").status == CHECK_INCONCLUSIVE
    assert evaluate_intent_review(review, candidate_snapshot="sha256:other", required_criterion_ids={"c"}).status == CHECK_INCONCLUSIVE
