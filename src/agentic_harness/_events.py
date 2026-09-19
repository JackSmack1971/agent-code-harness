"""Strict EventRegistry v1 validation and deterministic event envelopes."""
from __future__ import annotations

import datetime as dt
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from ._canonical import canonical_json_bytes, digest_for
from ._classification import SecretRegistration, redact_output
from ._contracts import find_contracts_root, load_yaml
from ._identity import uuid7_str


class EventRegistryError(ValueError):
    pass


def _registry(root: Path | None = None) -> dict[str, Any]:
    path = (root or find_contracts_root())
    if path is None:
        raise EventRegistryError("authoritative contracts unavailable")
    value = load_yaml(path / "event_registry.yaml")
    errors = sorted(Draft202012Validator(load_yaml(path / "event_registry.schema.json")).iter_errors(value), key=str)
    if errors:
        raise EventRegistryError(f"invalid EventRegistry contract: {errors[0].message}")
    return value


def registered_events(root: Path | None = None) -> dict[str, dict[str, Any]]:
    entries = _registry(root)["events"]
    result = {entry["event_type"]: entry for entry in entries}
    if len(result) != len(entries):
        raise EventRegistryError("duplicate event_type")
    return result


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    run_id: str
    sequence: int
    event_type: str
    event_version: int
    occurred_at: str
    actor_type: str
    actor_id: str | None
    causation_event_id: str | None
    correlation_id: str
    payload: dict[str, Any]
    payload_digest: str
    redaction_applied: bool

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())


def validate_payload(event_type: str, payload: dict[str, Any], *, root: Path | None = None) -> None:
    if not isinstance(payload, dict):
        raise EventRegistryError("event payload must be an object")
    entry = registered_events(root).get(event_type)
    if entry is None:
        raise EventRegistryError(f"unregistered event type: {event_type}")
    errors = sorted(Draft202012Validator(entry["payload_schema"]).iter_errors(payload), key=str)
    if errors:
        raise EventRegistryError(f"invalid payload for {event_type}: {errors[0].message}")


def make_event(*, run_id: str, sequence: int, event_type: str, payload: dict[str, Any], actor_type: str,
               actor_id: str | None = None, causation_event_id: str | None = None,
               correlation_id: str | None = None, occurred_at: dt.datetime | None = None,
               redaction_applied: bool = False, root: Path | None = None,
               secret_registrations: list[SecretRegistration] | None = None) -> EventEnvelope:
    if sequence < 1:
        raise EventRegistryError("event sequence must be >= 1")
    if actor_type not in {"RUNTIME", "USER", "CI", "TRUSTED_CI", "MODEL", "TOOL", "SUBAGENT", "SYSTEM", "EXTERNAL"}:
        raise EventRegistryError(f"invalid actor_type: {actor_type}")
    entries = registered_events(root)
    entry = entries.get(event_type)
    if entry is None:
        raise EventRegistryError(f"unregistered event type: {event_type}")
    # Redaction is performed before validation, digesting, and persistence;
    # callers cannot ask the event layer to persist a plaintext registered
    # secret and clean it only in a later projection.
    redacted_payload = redact_output(payload, secret_registrations or [])
    redaction_applied = redaction_applied or redacted_payload != payload
    validate_payload(event_type, redacted_payload, root=root)
    if sequence == 1 and causation_event_id is not None:
        raise EventRegistryError("first event cannot have causation_event_id")
    if sequence == 1 and correlation_id not in (None, run_id):
        raise EventRegistryError("first event correlation_id must equal run_id")
    at = occurred_at or dt.datetime.now(dt.timezone.utc)
    if at.tzinfo is None:
        raise EventRegistryError("occurred_at must be timezone-aware")
    return EventEnvelope(uuid7_str(), run_id, sequence, event_type, entry["schema_version"],
                         at.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z"), actor_type,
                         actor_id, causation_event_id, correlation_id or run_id,
                         redacted_payload, digest_for(redacted_payload), redaction_applied)


def jsonl_line(event: EventEnvelope) -> bytes:
    return event.canonical_bytes() + b"\n"
