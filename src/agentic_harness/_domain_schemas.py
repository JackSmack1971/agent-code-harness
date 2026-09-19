"""Runtime validator/digest support for `DomainSchemas v1` (Blueprint 9.6, 10.3, 10.15).

`contracts/domain_schemas.schema.json` is the sole authoritative, machine-readable
source for every Phase-0/Phase-1 durable record shape (Canonical Identity Rules:
"Canonical registries have exactly one machine-readable source consumed by
runtime and tests"; CLAUDE.md Scope Discipline: "do not duplicate canonical
state/config/event/effect/status registries in hand-maintained code"). This
module therefore does not redeclare the field lists as a second, hand-written
Pydantic type hierarchy; it validates instances strictly against that JSON
Schema (unknown fields rejected via `additionalProperties: false`, exactly
Blueprint 9.6.1's "forbid unknown fields" requirement) and computes/verifies
identity digests through the single canonical serialization implementation
in `_canonical.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from ._canonical import CanonicalizationError, digest_for
from ._contracts import find_contracts_root, load_json

REASON_CODE_INVALID_CONTRACT_VALUE = "CONFIG_INVALID_CONTRACT_VALUE"
REASON_CODE_UNKNOWN_KEY = "CONFIG_UNKNOWN_KEY"

_SCHEMAS_WITHOUT_DIGEST = frozenset({"ApprovalGrant"})


class DomainSchemaError(ValueError):
    """A domain record failed strict validation against DomainSchemas v1.

    Raised instead of silently accepting a malformed/unknown-field instance;
    callers MUST treat this as a rejection, never a partial/best-effort parse.
    """

    def __init__(self, message: str, *, reason_code: str = REASON_CODE_INVALID_CONTRACT_VALUE) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class DigestMismatchError(DomainSchemaError):
    """A record's declared `digest` does not equal its recomputed identity digest."""


@dataclass(frozen=True)
class _SchemaBundle:
    domain_schemas: dict[str, Any]
    semantic_types: dict[str, Any]
    registry: Registry


def _load_bundle(contracts_root: Path | None = None) -> _SchemaBundle:
    root = contracts_root or find_contracts_root()
    if root is None:
        raise DomainSchemaError(
            "contracts/ root not found; cannot validate a domain record without the authoritative schema"
        )
    domain_doc = load_json(root / "domain_schemas.schema.json")
    semantic_doc = load_json(root / "semantic_types.schema.json")
    registry = Registry().with_resources(
        [
            (semantic_doc["$id"], Resource.from_contents(semantic_doc)),
            (domain_doc["$id"], Resource.from_contents(domain_doc)),
        ]
    )
    return _SchemaBundle(domain_schemas=domain_doc, semantic_types=semantic_doc, registry=registry)


def registered_schema_names(contracts_root: Path | None = None) -> list[str]:
    bundle = _load_bundle(contracts_root)
    return list(bundle.domain_schemas["x-registered-schemas"])


def _validator_for(schema_name: str, bundle: _SchemaBundle) -> Draft202012Validator:
    if schema_name not in bundle.domain_schemas["$defs"]:
        raise DomainSchemaError(f"{schema_name!r} is not a registered DomainSchemas v1 type")
    ref = f"{bundle.domain_schemas['$id']}#/$defs/{schema_name}"
    return Draft202012Validator({"$ref": ref}, registry=bundle.registry)


def validate_record(schema_name: str, instance: dict[str, Any], *, contracts_root: Path | None = None) -> None:
    """Strictly validate `instance` against the named DomainSchemas v1 type.

    Raises `DomainSchemaError` (never returns a partially-accepted value) on
    any structural violation, including an unknown/extra field.
    """
    bundle = _load_bundle(contracts_root)
    validator = _validator_for(schema_name, bundle)
    errors = sorted(validator.iter_errors(instance), key=str)
    if not errors:
        return
    reason_code = REASON_CODE_INVALID_CONTRACT_VALUE
    for error in errors:
        if "Additional properties are not allowed" in error.message:
            reason_code = REASON_CODE_UNKNOWN_KEY
            break
    raise DomainSchemaError(
        f"{schema_name} failed DomainSchemas v1 validation: {[e.message for e in errors]}",
        reason_code=reason_code,
    )


def compute_identity_digest(schema_name: str, instance: dict[str, Any], *, contracts_root: Path | None = None) -> str:
    """Compute the CanonicalSerialization v1 digest of `instance`'s identity payload.

    The record is validated first. The `digest` field itself is excluded from
    its own digest input (9.6.1). Not defined for `ApprovalGrant`, which has
    no digest field.
    """
    if schema_name in _SCHEMAS_WITHOUT_DIGEST:
        raise DomainSchemaError(f"{schema_name} has no digest field to compute (9.6.3)")
    validate_record(schema_name, instance, contracts_root=contracts_root)
    payload = {key: value for key, value in instance.items() if key != "digest"}
    try:
        return digest_for(payload)
    except CanonicalizationError as exc:
        raise DomainSchemaError(str(exc), reason_code=exc.reason_code) from exc


def verify_record_digest(schema_name: str, instance: dict[str, Any], *, contracts_root: Path | None = None) -> None:
    """Validate `instance` and confirm its declared `digest` matches the recomputed one."""
    if schema_name in _SCHEMAS_WITHOUT_DIGEST:
        validate_record(schema_name, instance, contracts_root=contracts_root)
        return
    declared = instance.get("digest")
    recomputed = compute_identity_digest(schema_name, instance, contracts_root=contracts_root)
    if declared != recomputed:
        raise DigestMismatchError(
            f"{schema_name}.digest {declared!r} does not match the recomputed identity digest {recomputed!r}"
        )
