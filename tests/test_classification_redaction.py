from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentic_harness._classification import (
    CLASSIFICATION_ORDER,
    REDACTION_POINTS,
    ClassificationError,
    Provenance,
    SecretRegistration,
    TAINTS,
    classification_rank,
    derive_provenance,
    load_credential_formats,
    load_sensitive_field_names,
    max_classification,
    redact_registered_credential_formats,
    redact_output,
    redact_text,
    redact_value,
    union_taint,
)


def test_classification_order_matches_blueprint_10_3_8() -> None:
    assert CLASSIFICATION_ORDER == ("PUBLIC", "INTERNAL", "SENSITIVE", "SECRET")


def test_classification_rank_is_monotonic() -> None:
    ranks = [classification_rank(c) for c in CLASSIFICATION_ORDER]
    assert ranks == sorted(ranks)


def test_classification_rank_rejects_unregistered_value() -> None:
    with pytest.raises(ClassificationError):
        classification_rank("TOP_SECRET")


def test_max_classification_picks_the_highest() -> None:
    assert max_classification("PUBLIC", "SENSITIVE", "INTERNAL") == "SENSITIVE"


def test_max_classification_of_no_inputs_is_public() -> None:
    assert max_classification() == "PUBLIC"


def test_union_taint_combines_all_sets() -> None:
    result = union_taint(frozenset({"MODEL_GENERATED"}), frozenset({"REPOSITORY_UNTRUSTED"}))
    assert result == {"MODEL_GENERATED", "REPOSITORY_UNTRUSTED"}


def test_union_taint_never_removes_taint() -> None:
    a = frozenset({"SECRET_DERIVED"})
    result = union_taint(a, frozenset())
    assert "SECRET_DERIVED" in result


def test_taint_registry_is_closed() -> None:
    with pytest.raises(ClassificationError):
        union_taint(frozenset({"UNKNOWN_TAINT"}))
    assert "SECRET_DERIVED" in TAINTS


def test_derive_provenance_is_max_classification_and_union_taint() -> None:
    inputs = [
        Provenance(classification="PUBLIC", taint=frozenset({"MODEL_GENERATED"})),
        Provenance(classification="SENSITIVE", taint=frozenset({"REPOSITORY_UNTRUSTED"})),
    ]
    derived = derive_provenance(*inputs)
    assert derived.classification == "SENSITIVE"
    assert derived.taint == {"MODEL_GENERATED", "REPOSITORY_UNTRUSTED"}


def test_derive_provenance_of_no_inputs_is_untainted_public() -> None:
    derived = derive_provenance()
    assert derived == Provenance(classification="PUBLIC", taint=frozenset())


def test_no_declassify_function_is_exported() -> None:
    import agentic_harness._classification as mod

    assert not any("declassif" in name.lower() for name in dir(mod))


# ---------------------------------------------------------------------------
# Redaction Closure (10.11)
# ---------------------------------------------------------------------------


def test_redaction_points_match_blueprint_10_11() -> None:
    assert REDACTION_POINTS == ("EVENT_PERSISTENCE", "TOOL_OUTPUT_PERSISTENCE", "MODEL_CONTEXT_ADMISSION", "TELEMETRY_EXPORT", "CLI_RENDERING")


def test_redact_text_replaces_exact_known_secret() -> None:
    regs = [SecretRegistration(secret_id="openai_api_key", plaintext="sk-super-secret-value")]
    out = redact_text("the key is sk-super-secret-value here", regs)
    assert "sk-super-secret-value" not in out
    assert "<REDACTED:openai_api_key>" in out


def test_redact_text_leaves_unrelated_text_alone() -> None:
    regs = [SecretRegistration(secret_id="x", plaintext="abc123")]
    assert redact_text("nothing sensitive here", regs) == "nothing sensitive here"


def test_redact_text_matches_registered_derived_representation() -> None:
    regs = [SecretRegistration(secret_id="tok", plaintext="raw-secret", derived_representations=("cmF3LXNlY3JldA==",))]
    out = redact_text("encoded: cmF3LXNlY3JldA==", regs)
    assert "cmF3LXNlY3JldA==" not in out
    assert "<REDACTED:tok>" in out


def test_redact_text_does_not_perform_entropy_only_detection() -> None:
    # A high-entropy string that was never registered as a known secret is
    # NOT redacted: entropy-only detection is advisory, never the mechanism.
    high_entropy = "k3jD9sLp2QzXwYtRb7Nf8AeHc1MvGoUi"
    assert redact_text(high_entropy, []) == high_entropy


def test_redact_value_redacts_nested_structures() -> None:
    regs = [SecretRegistration(secret_id="s", plaintext="topsecret")]
    value = {"a": ["topsecret", {"b": "topsecret again"}]}
    out = redact_value(value, regs)
    assert "topsecret" not in json.dumps(out)


def test_redact_output_redacts_secret_in_dictionary_keys(contracts_root: Path) -> None:
    regs = [SecretRegistration(secret_id="s", plaintext="topsecret")]
    out = redact_output({"topsecret": "ordinary"}, regs, credential_formats=[])
    assert "topsecret" not in json.dumps(out)


def test_redact_output_applies_registered_credential_formats(contracts_root: Path) -> None:
    formats = load_credential_formats(contracts_root)
    out = redact_output({"value": "sk-abcdefghijklmnopqrstuvwx123"}, [], credential_formats=formats)
    assert "sk-abcdefghijklmnopqrstuvwx123" not in json.dumps(out)


def test_redact_value_redacts_schema_sensitive_field_regardless_of_content() -> None:
    value = {"password": "whatever-not-registered", "note": "fine"}
    out = redact_value(value, [], sensitive_field_names=frozenset({"password"}))
    assert out["password"] != "whatever-not-registered"
    assert out["note"] == "fine"


def test_load_credential_formats_matches_policy_contract_registry(contracts_root: Path) -> None:
    formats = load_credential_formats(contracts_root)
    assert {label for label, _pattern in formats} == {"OPENAI_API_KEY", "ANTHROPIC_API_KEY"}


def test_load_sensitive_field_names_reads_schema_annotations(contracts_root: Path, tmp_path: Path) -> None:
    schema = tmp_path / "sensitive.schema.json"
    schema.write_text(json.dumps({"type": "object", "properties": {"password": {"type": "string", "x-sensitive": True}}}), encoding="utf-8")
    assert load_sensitive_field_names(tmp_path) == frozenset({"password"})


def test_redact_registered_credential_formats_matches_openai_style_key(contracts_root: Path) -> None:
    formats = load_credential_formats(contracts_root)
    out = redact_registered_credential_formats("key=sk-abcdefghijklmnopqrstuvwx123", formats)
    assert "sk-abcdefghijklmnopqrstuvwx123" not in out


def test_redact_registered_credential_formats_leaves_ordinary_text_alone(contracts_root: Path) -> None:
    formats = load_credential_formats(contracts_root)
    text = "no secrets in here at all"
    assert redact_registered_credential_formats(text, formats) == text


def test_inv_secret_001_consistency_with_redact_text() -> None:
    from agentic_harness._invariants import inv_secret_001

    regs = [SecretRegistration(secret_id="s", plaintext="topsecret")]
    payload_with_secret = {"a": "topsecret"}
    assert inv_secret_001(payload_with_secret, frozenset({"topsecret"})) is False

    redacted = redact_value(payload_with_secret, regs)
    assert inv_secret_001(redacted, frozenset({"topsecret"})) is True


# ---------------------------------------------------------------------------
# Contract cross-check: policy_contract.yaml redaction closure matches this module
# ---------------------------------------------------------------------------


def test_policy_contract_redaction_closure_matches_runtime(contracts_root: Path) -> None:
    import yaml

    doc = yaml.safe_load((contracts_root / "policy_contract.yaml").read_text(encoding="utf-8"))
    assert tuple(doc["redaction"]["redaction_points"]) == REDACTION_POINTS
    assert doc["redaction"]["entropy_only_is_advisory_only"] is True


def test_policy_contract_schema_is_valid(contracts_root: Path) -> None:
    schema = json.loads((contracts_root / "policy_contract.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
