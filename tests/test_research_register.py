from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REQUIRED_RESEARCH_IDS = {
    "GIT_MIN_VERSION",
    "GIT_WORKTREE_BEHAVIOR",
    "GIT_SHA256_REPOSITORY_SUPPORT",
    "GIT_SPARSE_CHECKOUT_BEHAVIOR",
    "WINDOWS_GIT_FILEMODE_CASE_BEHAVIOR",
    "PYTHON_SUPPORTED_SQLITE_MATRIX",
    "FILESYSTEM_ATOMIC_REPLACE_AND_FSYNC",
    "POSIX_PROCESS_GROUP_TERMINATION",
    "WINDOWS_JOB_OBJECT_TERMINATION",
    "DOCKER_PODMAN_ISOLATION",
    "SCOPED_NETWORK_ENFORCEMENT",
    "OPENAI_ADAPTER_SEMANTICS",
    "ANTHROPIC_ADAPTER_SEMANTICS",
    "OPENROUTER_ADAPTER_SEMANTICS",
    "TOKEN_COUNTING_APIS",
    "TREESITTER_SUPPORT_MATRIX",
    "LOCK_OWNERSHIP_STALENESS",
    "MCP_PROTOCOL_SDK",
    "OTEL_PYTHON_EXPORTER",
    "GITHUB_ACTIONS_TRUST_TOKEN",
    "PACKAGE_INDEX_NAME_AVAILABILITY",
}


def _register_and_schema(contracts_root: Path) -> tuple[dict, dict]:
    register = yaml.safe_load((contracts_root / "research_register.yaml").read_text(encoding="utf-8"))
    schema = json.loads((contracts_root / "research_register.schema.json").read_text(encoding="utf-8"))
    return register, schema


def test_research_register_validates_against_its_schema(contracts_root: Path) -> None:
    register, schema = _register_and_schema(contracts_root)
    Draft202012Validator(schema).validate(register)


def test_all_blueprint_mandated_research_ids_are_present(contracts_root: Path) -> None:
    register, _ = _register_and_schema(contracts_root)
    ids = {r["research_id"] for r in register["records"]}
    missing = REQUIRED_RESEARCH_IDS - ids
    assert not missing, f"missing required research records: {sorted(missing)}"


def test_research_ids_are_unique(contracts_root: Path) -> None:
    register, _ = _register_and_schema(contracts_root)
    ids = [r["research_id"] for r in register["records"]]
    assert len(ids) == len(set(ids))


def test_unresolved_records_declare_fail_closed_behavior(contracts_root: Path) -> None:
    register, _ = _register_and_schema(contracts_root)
    for record in register["records"]:
        if record["resolved_value"] is None:
            assert record["failure_behavior"] in ("BLOCKED_CAPABILITY", "UNSUPPORTED", "DEGRADED_DECLARED")
            assert record["verified_at"] is None


def test_git_min_version_is_resolved_with_evidence(contracts_root: Path) -> None:
    register, _ = _register_and_schema(contracts_root)
    by_id = {r["research_id"]: r for r in register["records"]}
    record = by_id["GIT_MIN_VERSION"]
    assert record["resolved_value"] == "2.35.3"
    assert record["source_refs"], "resolved record must cite authoritative sources"
    assert record["verified_at"] is not None


def test_malformed_register_with_unknown_field_is_rejected(contracts_root: Path) -> None:
    register, schema = _register_and_schema(contracts_root)
    register["records"][0]["unexpected_field"] = "nope"
    validator = Draft202012Validator(schema)
    assert not validator.is_valid(register)


def test_resolved_record_without_source_refs_is_rejected(contracts_root: Path) -> None:
    register, schema = _register_and_schema(contracts_root)
    bad = dict(register["records"][0])
    bad["resolved_value"] = "9.9.9"
    bad["source_refs"] = []
    validator = Draft202012Validator(schema)
    assert not validator.is_valid({**register, "records": [bad]})
