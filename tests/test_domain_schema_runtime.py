from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from agentic_harness import _domain_schemas
from agentic_harness._domain_schemas import (
    DigestMismatchError,
    DomainSchemaError,
    compute_identity_digest,
    registered_schema_names,
    validate_record,
    verify_record_digest,
)

RUN_RECORD: dict[str, Any] = {
    "schema_name": "RunRecord",
    "schema_version": 1,
    "run_id": "018f1e2e-0000-7000-8000-000000000000",
    "state": "CREATED",
    "run_version": 0,
    "goal_revision_id": None,
    "change_revision_id": None,
    "repository_snapshot_digest": None,
    "candidate_snapshot_digest": None,
    "config_digest": None,
    "policy_digest": None,
    "resume_target_state": None,
    "created_at": "2026-09-19T00:00:00Z",
    "updated_at": "2026-09-19T00:00:00Z",
    "digest": "sha256:" + "a" * 64,
}

APPROVAL_GRANT: dict[str, Any] = {
    "schema_name": "ApprovalGrant",
    "schema_version": 1,
    "approval_id": "018f1e2e-0000-7000-8000-000000000001",
    "request_digest": "sha256:" + "b" * 64,
    "disposition": "ALLOW_ONCE",
    "actor_type": "USER",
    "actor_id": "u1",
    "issued_at": "2026-09-19T00:00:00Z",
    "expires_at": None,
    "revoked_at": None,
    "consumption_limit": 1,
    "consumed_count": 0,
}


def test_registered_schema_names_matches_the_blueprint_minimum_set() -> None:
    names = set(registered_schema_names())
    assert names == {
        "GoalContract", "ChangeContract", "VerificationPlan", "RepositorySnapshot", "CandidateSnapshot",
        "VerificationResult", "EvidenceManifest", "ApprovalRequest", "ApprovalGrant", "IntentReviewResult",
        "RunRecord", "CheckpointRecord", "ArtifactRecord", "ToolCallRecord", "ModelCallRecord",
        "SubagentExecutionRecord", "AcceptanceRequest", "IntegrationRecord", "QualifiedDefault",
    }


def test_validate_record_accepts_a_structurally_valid_instance() -> None:
    validate_record("RunRecord", RUN_RECORD)


def test_validate_record_rejects_unknown_field() -> None:
    bad = dict(RUN_RECORD, unexpected="x")
    with pytest.raises(DomainSchemaError) as excinfo:
        validate_record("RunRecord", bad)
    assert excinfo.value.reason_code == "CONFIG_UNKNOWN_KEY"


def test_validate_record_rejects_unregistered_schema_name() -> None:
    with pytest.raises(DomainSchemaError):
        validate_record("NotARealSchema", RUN_RECORD)


def test_compute_identity_digest_excludes_the_digest_field_itself() -> None:
    with_a = dict(RUN_RECORD, digest="sha256:" + "a" * 64)
    with_b = dict(RUN_RECORD, digest="sha256:" + "b" * 64)
    assert compute_identity_digest("RunRecord", with_a) == compute_identity_digest("RunRecord", with_b)


def test_compute_identity_digest_changes_when_identity_payload_changes() -> None:
    changed = dict(RUN_RECORD, run_version=1)
    assert compute_identity_digest("RunRecord", RUN_RECORD) != compute_identity_digest("RunRecord", changed)


def test_verify_record_digest_accepts_a_correctly_computed_digest() -> None:
    record = dict(RUN_RECORD)
    record["digest"] = compute_identity_digest("RunRecord", record)
    verify_record_digest("RunRecord", record)


def test_verify_record_digest_rejects_a_stale_digest() -> None:
    record = dict(RUN_RECORD)
    record["digest"] = compute_identity_digest("RunRecord", record)
    record["run_version"] = 1
    with pytest.raises(DigestMismatchError):
        verify_record_digest("RunRecord", record)


def test_compute_identity_digest_refuses_approval_grant() -> None:
    with pytest.raises(DomainSchemaError):
        compute_identity_digest("ApprovalGrant", APPROVAL_GRANT)


def test_verify_record_digest_only_structurally_validates_approval_grant() -> None:
    verify_record_digest("ApprovalGrant", APPROVAL_GRANT)
    bad = dict(APPROVAL_GRANT, digest="sha256:" + "c" * 64)
    with pytest.raises(DomainSchemaError):
        verify_record_digest("ApprovalGrant", bad)


def test_digest_is_stable_across_key_insertion_order() -> None:
    reordered = dict(reversed(list(RUN_RECORD.items())))
    assert compute_identity_digest("RunRecord", RUN_RECORD) == compute_identity_digest("RunRecord", reordered)


def test_module_reason_codes_are_registered_in_reason_code_registry(contracts_root: Path) -> None:
    """_domain_schemas.py's REASON_CODE_* constants must be members of the sole
    authoritative ReasonCodeRegistry v1, not free-standing string literals that
    could silently drift from it."""
    registry = yaml.safe_load((contracts_root / "reason_code_registry.yaml").read_text(encoding="utf-8"))
    known_codes = {c["code"] for c in registry["codes"]}
    assert _domain_schemas.REASON_CODE_INVALID_CONTRACT_VALUE in known_codes
    assert _domain_schemas.REASON_CODE_UNKNOWN_KEY in known_codes


def test_revision_material_change_produces_a_new_identity_digest_not_a_mutation() -> None:
    """INV-REVISION-001-adjacent: a material field change must be representable as a
    distinct identity (new digest), never silently accepted as 'the same' record."""
    revised = copy.deepcopy(RUN_RECORD)
    revised["state"] = "REPOSITORY_READY"
    original_digest = compute_identity_digest("RunRecord", RUN_RECORD)
    revised_digest = compute_identity_digest("RunRecord", revised)
    assert original_digest != revised_digest
