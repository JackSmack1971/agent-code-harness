"""Independent second CanonicalSerialization v1 encoder, used only to
cross-check `agentic_harness._canonical` byte-for-byte on the golden and
property-test vectors (9.5.6: "byte-for-byte golden vectors match across
the primary serializer and an independent fixture implementation").

Deliberately does NOT import or reuse `agentic_harness._canonical` and does
NOT use `json.dumps` for byte emission: it walks the canonical tree and
hand-writes UTF-8 JSON text itself, so an escaping/ordering bug in the
primary implementation's use of `json.dumps` would not be silently mirrored
here. This module is test-only scaffolding, not a second production
canonicalizer (Canonical Identity Rules: exactly one canonical
implementation is authoritative for runtime use).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import uuid
from decimal import Decimal
from enum import Enum
from typing import Any

DIGEST_PREFIX = "sha256:"


class ReferenceCanonicalizationError(ValueError):
    pass


def _encode_string(value: str) -> str:
    for ch in value:
        cp = ord(ch)
        if 0xD800 <= cp <= 0xDFFF:
            raise ReferenceCanonicalizationError(f"lone surrogate U+{cp:04X}")
    value.encode("utf-8", errors="strict")

    out = ['"']
    for ch in value:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20:
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _encode_decimal(value: Decimal) -> str:
    if value.is_nan() or value.is_infinite():
        raise ReferenceCanonicalizationError(f"non-finite Decimal {value!r}")
    sign, digits, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        raise ReferenceCanonicalizationError(f"special Decimal exponent {value!r}")

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


def _encode_datetime(value: _dt.datetime) -> str:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ReferenceCanonicalizationError(f"naive datetime {value!r}")
    utc_value = value.astimezone(_dt.timezone.utc)
    base = utc_value.strftime("%Y-%m-%dT%H:%M:%S")
    if utc_value.microsecond:
        return f"{base}.{utc_value.microsecond:06d}Z"
    return f"{base}Z"


def _encode(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        raise ReferenceCanonicalizationError("float forbidden")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, bytes):
        raise ReferenceCanonicalizationError("bytes forbidden")
    if isinstance(value, str):
        return _encode_string(value)
    if isinstance(value, Decimal):
        return _encode_string(_encode_decimal(value))
    if isinstance(value, uuid.UUID):
        return _encode_string(str(value))
    if isinstance(value, Enum):
        return _encode_string(str(value.value))
    if isinstance(value, _dt.datetime):
        return _encode_string(_encode_datetime(value))
    if isinstance(value, _dt.date):
        return _encode_string(value.isoformat())
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise ReferenceCanonicalizationError(f"non-string key {key!r}")
        ordered_keys = sorted(value.keys(), key=lambda k: k.encode("utf-8"))
        body = ",".join(f"{_encode_string(k)}:{_encode(value[k])}" for k in ordered_keys)
        return "{" + body + "}"
    if isinstance(value, (set, frozenset)):
        encoded_elements = sorted(_encode(item) for item in value)
        return "[" + ",".join(encoded_elements) + "]"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    raise ReferenceCanonicalizationError(f"unsupported type {type(value)!r}")


def reference_canonical_json_text(value: Any) -> str:
    return _encode(value)


def reference_canonical_json_bytes(value: Any) -> bytes:
    return _encode(value).encode("utf-8")


def reference_digest_for(value: Any) -> str:
    return DIGEST_PREFIX + hashlib.sha256(reference_canonical_json_bytes(value)).hexdigest()
