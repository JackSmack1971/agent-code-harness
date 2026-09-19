"""Offline Phase-0J fixture and closure checks."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from agentic_harness._side_effects import RecoveryClassification, retry_allowed


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_prescribed_phase0j_fixture_groups_are_materialized() -> None:
    groups = {
        "recovery",
        "resource_normalization",
        "side_effect_transactions",
        "repository_identity",
        "event_payloads",
        "cli_data_schemas",
        "research_register",
    }
    for group in groups:
        directory = CONTRACTS / "tests" / group
        assert (directory / "golden.json").is_file(), group
        assert any(directory.glob("adversarial.json")) or group == "repository_identity", group
    assert (CONTRACTS / "tests" / "repository_identity" / "golden_repos" / "index.json").is_file()


def test_event_payload_golden_and_adversarial_fixtures() -> None:
    events = {item["event_type"]: item for item in _yaml(CONTRACTS / "event_registry.yaml")["events"]}
    for case in _json(CONTRACTS / "tests/event_payloads/golden.json"):
        Draft202012Validator(events[case["event_type"]]["payload_schema"]).validate(case["payload"])
    for case in _json(CONTRACTS / "tests/event_payloads/adversarial.json"):
        if case["event_type"] not in events:
            continue
        assert not Draft202012Validator(events[case["event_type"]]["payload_schema"]).is_valid(case["payload"])


def test_recovery_and_side_effect_golden_relations_are_authoritative() -> None:
    state = _yaml(CONTRACTS / "state_machine.yaml")
    actual = []
    for item in state["recovery_transitions"]:
        if item.get("branches"):
            actual.extend({**{key: item[key] for key in ("source_state", "target_mode")}, **branch} for branch in item["branches"])
        else:
            actual.append({key: item[key] for key in ("source_state", "target_mode", "command")})
    expected = _json(CONTRACTS / "tests/recovery/golden.json")
    assert {json.dumps(item, sort_keys=True) for item in actual} == {json.dumps(item, sort_keys=True) for item in expected}

    for case in _json(CONTRACTS / "tests/side_effect_transactions/golden.json"):
        assert retry_allowed(RecoveryClassification(case["classification"])) is case["retry_allowed"]
    for case in _json(CONTRACTS / "tests/side_effect_transactions/adversarial.json"):
        assert case["retry_allowed"] is True
        assert retry_allowed(RecoveryClassification(case["classification"])) is False


def test_cli_data_golden_and_adversarial_fixtures() -> None:
    for case in _json(CONTRACTS / "tests/cli_data_schemas/golden.json"):
        schema = _json(CONTRACTS / f"cli_protocol/data/{case['command']}.schema.json")
        Draft202012Validator(schema).validate(case["data"])
    for case in _json(CONTRACTS / "tests/cli_data_schemas/adversarial.json"):
        schema = _json(CONTRACTS / f"cli_protocol/data/{case['command']}.schema.json")
        assert not Draft202012Validator(schema).is_valid(case["data"])


def test_research_fixture_cannot_turn_unresolved_facts_into_support() -> None:
    records = {item["research_id"]: item for item in _yaml(CONTRACTS / "research_register.yaml")["records"]}
    allowed = {"UNSUPPORTED", "BLOCKED_CAPABILITY", "DEGRADED_DECLARED"}
    for case in _json(CONTRACTS / "tests/research_register/golden.json"):
        record = records[case["research_id"]]
        assert (record["resolved_value"] is not None) is case["resolved"]
        assert record["failure_behavior"] == case["failure_behavior"]
    for case in _json(CONTRACTS / "tests/research_register/adversarial.json"):
        assert case["failure_behavior"] not in allowed
