"""Data Classification/Taint propagation and Redaction Closure (Blueprint 10.3.8, 10.11).

`DataClassification`/`Taint` shapes are owned by `semantic_types.schema.json`
(materialized in Phase 0C); this module owns the propagation and redaction
*logic* those types don't carry on their own, plus the redaction-source
registry consumed from `contracts/policy_contract.yaml#/redaction`
(`PolicyContract v1`, materialized this phase). No classification order or
redaction rule is invented here that is not already in one of those two
contracts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from ._contracts import find_contracts_root, load_json, load_yaml

REASON_CODE_INVALID_CONTRACT_VALUE = "CONFIG_INVALID_CONTRACT_VALUE"

# 10.3.8 canonical ascending order. Single authoritative ordering, mirrored
# from semantic_types.schema.json#/$defs/DataClassificationOrder (a `const`
# there; duplicated here only as the runtime index table that JSON Schema
# cannot itself provide).
CLASSIFICATION_ORDER: tuple[str, ...] = ("PUBLIC", "INTERNAL", "SENSITIVE", "SECRET")
_CLASSIFICATION_RANK = {name: rank for rank, name in enumerate(CLASSIFICATION_ORDER)}
TAINTS: frozenset[str] = frozenset({
    "SECRET_DERIVED", "USER_PRIVATE", "REPOSITORY_UNTRUSTED",
    "EXTERNAL_UNTRUSTED", "MODEL_GENERATED", "TOOL_OUTPUT_UNTRUSTED",
})


@lru_cache(maxsize=8)
def _semantic_registry(contracts_root: Path | None = None) -> tuple[tuple[str, ...], frozenset[str]]:
    root = contracts_root or find_contracts_root()
    if root is None:
        raise ClassificationError("contracts/ root not found; classification authority is unavailable")
    document = load_json(root / "semantic_types.schema.json")
    definitions = document["$defs"]
    return tuple(definitions["DataClassificationOrder"]["const"]), frozenset(definitions["Taint"]["enum"])


def classification_order(contracts_root: Path | None = None) -> tuple[str, ...]:
    try:
        return _semantic_registry(contracts_root)[0]
    except (OSError, KeyError, TypeError, ClassificationError) as exc:
        raise ClassificationError(f"classification registry unavailable: {exc}") from exc

REDACTION_MARKER_TEMPLATE = "<REDACTED:{secret_id}>"


class ClassificationError(ValueError):
    def __init__(self, message: str, *, reason_code: str = REASON_CODE_INVALID_CONTRACT_VALUE) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def classification_rank(classification: str) -> int:
    try:
        return classification_order().index(classification)
    except (ValueError, ClassificationError):
        raise ClassificationError(f"{classification!r} is not a registered DataClassification value") from None


def max_classification(*classifications: str) -> str:
    """10.3.8: derived content receives max(classification(inputs))."""
    order = classification_order()
    if not classifications:
        return order[0]
    return order[max(classification_rank(c) for c in classifications)]


def union_taint(*taint_sets: frozenset[str]) -> frozenset[str]:
    """10.3.8: derived content receives the union of input taints. No automatic
    secret declassification exists in v1: this function only ever adds taint,
    never removes it, and there is no companion "declassify" function.
    """
    result: frozenset[str] = frozenset()
    for taints in taint_sets:
        try:
            registered_taints = _semantic_registry()[1]
        except (OSError, KeyError, TypeError, ClassificationError) as exc:
            raise ClassificationError(f"taint registry unavailable: {exc}") from exc
        unknown = set(taints) - registered_taints
        if unknown:
            raise ClassificationError(f"unregistered taint value(s): {sorted(unknown)}")
        result = result | taints
    return result


@dataclass(frozen=True)
class Provenance:
    classification: str
    taint: frozenset[str]


def derive_provenance(*inputs: Provenance) -> Provenance:
    """Compute a derived value's classification/taint from its governing inputs (10.3.8)."""
    if not inputs:
        return Provenance(classification=classification_order()[0], taint=frozenset())
    return Provenance(
        classification=max_classification(*(p.classification for p in inputs)),
        taint=union_taint(*(p.taint for p in inputs)),
    )


# ---------------------------------------------------------------------------
# Redaction Closure (10.11 / policy_contract.yaml#/redaction)
# ---------------------------------------------------------------------------

REDACTION_POINTS = ("EVENT_PERSISTENCE", "TOOL_OUTPUT_PERSISTENCE", "MODEL_CONTEXT_ADMISSION", "TELEMETRY_EXPORT", "CLI_RENDERING")


@dataclass(frozen=True)
class SecretRegistration:
    """A broker-registered exact secret value plus its known deterministic derived
    representations (10.11: "the broker may register deterministic derived
    representations... only when the transformation is explicitly supported").
    """

    secret_id: str
    plaintext: str
    derived_representations: tuple[str, ...] = ()


def _known_values(registrations: list[SecretRegistration]) -> list[tuple[str, str]]:
    """Return (value, secret_id) pairs, longest value first so a derived
    representation that happens to contain a shorter one is matched by its
    own more specific registration first.
    """
    pairs: list[tuple[str, str]] = []
    for reg in registrations:
        if reg.plaintext:
            pairs.append((reg.plaintext, reg.secret_id))
        for derived in reg.derived_representations:
            if derived:
                pairs.append((derived, reg.secret_id))
    return sorted(pairs, key=lambda pair: len(pair[0]), reverse=True)


def redact_text(text: str, registrations: list[SecretRegistration]) -> str:
    """Exact-match redaction: replace every occurrence of a registered secret
    value (or its registered derived representation) with its typed marker.
    Entropy-only detection is intentionally not implemented as a redaction
    mechanism (10.11: advisory only, never the sole mechanism); this
    function performs only exact matching.
    """
    result = text
    for value, secret_id in _known_values(registrations):
        if value in result:
            result = result.replace(value, REDACTION_MARKER_TEMPLATE.format(secret_id=secret_id))
    return result


def redact_value(
    value: Any,
    registrations: list[SecretRegistration],
    *,
    sensitive_field_names: frozenset[str] = frozenset(),
    credential_formats: list[tuple[str, re.Pattern[str]]] | None = None,
) -> Any:
    """Recursively redact a JSON-compatible value before it crosses a redaction
    point (10.11). `sensitive_field_names` implements the `x-sensitive: true`
    schema-field source: any dict key in that set has its entire value
    replaced with a generic marker regardless of exact-match, because a
    schema-declared-sensitive field is redacted by shape, not by content
    matching (10.11 source 1, "schema fields marked x-sensitive: true").
    """
    if isinstance(value, str):
        result = redact_text(value, registrations)
        for label, pattern in credential_formats or []:
            result = pattern.sub(REDACTION_MARKER_TEMPLATE.format(secret_id=f"FORMAT:{label}"), result)
        return result
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, sub_value in value.items():
            if key in sensitive_field_names:
                redacted_key = key
                redacted[redacted_key] = REDACTION_MARKER_TEMPLATE.format(secret_id="SCHEMA_SENSITIVE_FIELD")
            else:
                redacted_key = redact_value(key, registrations, credential_formats=credential_formats)
                redacted[redacted_key] = redact_value(
                    sub_value,
                    registrations,
                    sensitive_field_names=sensitive_field_names,
                    credential_formats=credential_formats,
                )
        return redacted
    if isinstance(value, list):
        return [redact_value(item, registrations, sensitive_field_names=sensitive_field_names, credential_formats=credential_formats) for item in value]
    return value


def load_credential_formats(contracts_root: Path | None = None) -> list[tuple[str, re.Pattern[str]]]:
    """10.11 source 3's registry: `policy_contract.yaml#/redaction/credential_formats`
    is the sole authoritative source (Canonical Identity Rules); this is the
    only place that registry is compiled, never a second hand-maintained
    copy of the pattern list.
    """
    root = contracts_root or find_contracts_root()
    if root is None:
        raise ClassificationError("contracts/ root not found; cannot load the credential-format registry")
    doc = load_yaml(root / "policy_contract.yaml")
    return [(entry["label"], re.compile(entry["pattern"])) for entry in doc["redaction"]["credential_formats"]]


def load_sensitive_field_names(contracts_root: Path | None = None) -> frozenset[str]:
    """Derive schema-declared sensitive field names from contract sources."""
    root = contracts_root or find_contracts_root()
    if root is None:
        raise ClassificationError("contracts/ root not found; cannot load sensitive-field declarations")
    names: set[str] = set()

    def visit(node: Any, property_name: str | None = None) -> None:
        if not isinstance(node, dict):
            return
        if node.get("x-sensitive") is True and property_name is not None:
            names.add(property_name)
        properties = node.get("properties")
        if isinstance(properties, dict):
            for name, child in properties.items():
                visit(child, name)
        for key, child in node.items():
            if key != "properties":
                visit(child, property_name)

    for schema_path in root.rglob("*.schema.json"):
        visit(load_json(schema_path))
    return frozenset(names)


def redact_registered_credential_formats(text: str, credential_formats: list[tuple[str, re.Pattern[str]]]) -> str:
    """10.11 source 3: registered credential formats required by enabled adapters.

    This is a distinct, narrower mechanism from exact-known-secret matching:
    it recognizes a *format* the harness's own adapters emit/consume, not an
    arbitrary high-entropy string (which redaction Closure explicitly
    forbids treating as sufficient on its own). `credential_formats` comes
    from `load_credential_formats` (or an equivalent already-loaded
    registry); this function performs no I/O itself.
    """
    result = text
    for label, pattern in credential_formats:
        result = pattern.sub(REDACTION_MARKER_TEMPLATE.format(secret_id=f"FORMAT:{label}"), result)
    return result


def redact_output(
    value: Any,
    registrations: list[SecretRegistration],
    *,
    sensitive_field_names: frozenset[str] | None = None,
    credential_formats: list[tuple[str, re.Pattern[str]]] | None = None,
) -> Any:
    """Apply every v1 redaction source before persistence or egress.

    Callers may pass the already-loaded credential registry to keep this
    function pure.  If omitted, the authoritative PolicyContract registry is
    loaded; no heuristic or unbounded transformation guessing is performed.
    """
    formats = credential_formats if credential_formats is not None else load_credential_formats()
    fields = sensitive_field_names if sensitive_field_names is not None else load_sensitive_field_names()
    return redact_value(
        value,
        registrations,
        sensitive_field_names=fields,
        credential_formats=formats,
    )
