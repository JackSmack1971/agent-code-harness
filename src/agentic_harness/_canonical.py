"""CanonicalSerialization v1 reference implementation (Blueprint 9.5, 10.4).

This is the single canonical serialization implementation for the harness.
Canonical Identity Rules: "Never add subsystem-local serialization or digest
helpers." Every digest-bearing durable object MUST go through
`canonical_json_bytes` / `digest_for` in this module rather than a
locally-written `json.dumps(..., sort_keys=True)` or similar.

Pipeline: typed value -> `to_canonical_value` (JSON-compatible tree with
UUID/date/datetime/Decimal/set normalization applied) -> `canonical_json_bytes`
(deterministic UTF-8 JSON bytes) -> `digest_for` (sha256:<hex>).

The golden and adversarial vectors this module is conformance-tested against
live in `contracts/canonical_serialization.yaml`, the sole machine-readable
authority for the rule set (contracts/canonical_serialization.schema.json).
"""

from __future__ import annotations

import datetime as _dt
import json
import uuid
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

DIGEST_PREFIX = "sha256:"
DEFAULT_MAX_DECIMAL_DIGITS = 200
REASON_CODE_INVALID_CONTRACT_VALUE = "CONFIG_INVALID_CONTRACT_VALUE"


class CanonicalizationError(ValueError):
    """A value could not be canonicalized because it violates CanonicalSerialization v1.

    Malformed values fail closed: this is always raised rather than the
    value being silently truncated, coerced, or dropped.
    """

    def __init__(self, message: str, *, reason_code: str = REASON_CODE_INVALID_CONTRACT_VALUE) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def _reject(message: str) -> None:
    raise CanonicalizationError(message)


def _check_unicode_scalar_string(value: str) -> str:
    for ch in value:
        cp = ord(ch)
        if 0xD800 <= cp <= 0xDFFF:
            _reject(f"string contains a lone UTF-16 surrogate scalar value U+{cp:04X}")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        _reject(f"string is not valid UTF-8: {exc}")
    return value


def format_decimal(value: Decimal, *, max_digit_count: int = DEFAULT_MAX_DECIMAL_DIGITS) -> str:
    """Normalize a Decimal per 10.4.3: no exponent, no leading '+', signed
    zero -> '0', trailing fractional zeros removed, decimal point removed
    when the fraction becomes empty. Independent of ambient Decimal context
    precision; uses the value's exact coefficient/exponent representation.
    """
    if value.is_nan() or value.is_infinite():
        _reject(f"Decimal value {value!r} is NaN/sNaN/Infinite, which CanonicalSerialization v1 forbids")

    sign, digits, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        _reject(f"Decimal value {value!r} has a non-finite special exponent")
    if len(digits) > max_digit_count:
        _reject(
            f"Decimal value has {len(digits)} significant digits, exceeding the configured "
            f"resource limit of {max_digit_count}"
        )

    digits_str = "".join(str(d) for d in digits) or "0"
    digit_count = len(digits_str)

    if exponent >= 0:
        int_part = digits_str + ("0" * exponent)
        frac_part = ""
    else:
        point = digit_count + exponent
        if point <= 0:
            int_part = "0"
            frac_part = ("0" * (-point)) + digits_str
        else:
            int_part = digits_str[:point]
            frac_part = digits_str[point:]

    frac_part = frac_part.rstrip("0")
    int_part = int_part.lstrip("0") or "0"

    result = int_part if not frac_part else f"{int_part}.{frac_part}"
    if sign and result != "0":
        result = f"-{result}"
    return result


def format_datetime(value: _dt.datetime) -> str:
    """Normalize a timezone-aware datetime per 10.4.2. Naive datetimes are invalid."""
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        _reject(f"datetime {value!r} is naive; CanonicalSerialization v1 requires a timezone-aware value")
    utc_value = value.astimezone(_dt.timezone.utc)
    base = utc_value.strftime("%Y-%m-%dT%H:%M:%S")
    if utc_value.microsecond:
        return f"{base}.{utc_value.microsecond:06d}Z"
    return f"{base}Z"


def format_date(value: _dt.date) -> str:
    return value.isoformat()


def format_uuid(value: uuid.UUID) -> str:
    return str(value)


def _sorted_object_keys(mapping: dict[Any, Any]) -> list[str]:
    keys: list[str] = []
    for key in mapping.keys():
        if not isinstance(key, str):
            _reject(f"object key {key!r} is not a string")
        keys.append(_check_unicode_scalar_string(key))
    return sorted(keys, key=lambda k: k.encode("utf-8"))


def to_canonical_value(value: Any, *, max_decimal_digits: int = DEFAULT_MAX_DECIMAL_DIGITS) -> Any:
    """Convert a typed Python value into a JSON-compatible canonical tree.

    Accepts: None, bool, int (not bool subtype float), str, dict[str, Any],
    list/tuple, set/frozenset, uuid.UUID, Enum, datetime.datetime,
    datetime.date (but not datetime.datetime, which is checked first since
    datetime is a date subclass), decimal.Decimal.

    Raises CanonicalizationError for float, bytes, or any other unsupported
    type, matching 9.5.2's forbidden-float/bytes rule and the requirement
    that a domain contract-defined type normalize to one of these values
    before reaching the serializer.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        _reject("float values are forbidden in identity-bearing canonical objects; use Decimal")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return _check_unicode_scalar_string(value)
    if isinstance(value, bytes):
        _reject("raw bytes are forbidden directly; store an artifact/digest reference instead")
    if isinstance(value, Decimal):
        try:
            return format_decimal(value, max_digit_count=max_decimal_digits)
        except InvalidOperation as exc:  # pragma: no cover - as_tuple() should not raise
            _reject(f"invalid Decimal value: {exc}")
    if isinstance(value, uuid.UUID):
        return format_uuid(value)
    if isinstance(value, Enum):
        member_value = value.value
        if not isinstance(member_value, str):
            _reject(f"Enum member {value!r} does not declare a stable string value")
        return _check_unicode_scalar_string(member_value)
    if isinstance(value, _dt.datetime):
        return format_datetime(value)
    if isinstance(value, _dt.date):
        return format_date(value)
    if isinstance(value, dict):
        sorted_keys = _sorted_object_keys(value)
        return {key: to_canonical_value(value[key], max_decimal_digits=max_decimal_digits) for key in sorted_keys}
    if isinstance(value, (set, frozenset)):
        elements = [to_canonical_value(item, max_decimal_digits=max_decimal_digits) for item in value]
        return sorted(elements, key=lambda item: canonical_json_bytes(item))
    if isinstance(value, (list, tuple)):
        return [to_canonical_value(item, max_decimal_digits=max_decimal_digits) for item in value]
    _reject(f"unsupported type for canonical serialization: {type(value)!r}")
    raise AssertionError("unreachable")  # pragma: no cover


def canonical_json_bytes(value: Any, *, max_decimal_digits: int = DEFAULT_MAX_DECIMAL_DIGITS) -> bytes:
    """Serialize a typed value to canonical UTF-8 JSON bytes (9.5.4).

    `value` may already be a canonical tree (as produced by
    `to_canonical_value`) or a raw typed value; both are accepted so this
    function can be used recursively (e.g. by set-element sorting) without
    double-normalizing.
    """
    canonical = to_canonical_value(value, max_decimal_digits=max_decimal_digits)
    text = json.dumps(canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    return text.encode("utf-8")


def digest_for(value: Any, *, max_decimal_digits: int = DEFAULT_MAX_DECIMAL_DIGITS) -> str:
    """Compute the `sha256:<hex>` digest of a value's canonical bytes (9.5.4)."""
    import hashlib

    payload = canonical_json_bytes(value, max_decimal_digits=max_decimal_digits)
    return DIGEST_PREFIX + hashlib.sha256(payload).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, val in pairs:
        if key in seen:
            _reject(f"duplicate object key {key!r} in untrusted JSON input")
        seen[key] = val
    return seen


def parse_untrusted_json(text: str) -> Any:
    """Parse untrusted JSON text, rejecting duplicate object keys (9.5.3).

    Native Python `dict` construction cannot itself hold duplicate keys, so
    this decoding boundary is where the "duplicate keys are invalid before
    serialization" rule is actually enforced for externally supplied JSON.
    """
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        _reject(f"input is not valid JSON: {exc}")
        raise AssertionError("unreachable")  # pragma: no cover
