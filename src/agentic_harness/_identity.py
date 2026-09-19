"""Harness-owned RFC 9562 UUIDv7 generator (Blueprint 10.3.2).

Python-version differences in stdlib `uuid` (no `uuid.uuid7()` before 3.14,
and no contractual guarantee of RFC 9562 bit-layout stability even once
added) must not alter durable identity, so the harness owns this generator
rather than depending on a version-sensitive stdlib/third-party function.

Layout (128 bits, MSB to LSB):
    48 bits  unix_ts_ms
     4 bits  version (0b0111)
    12 bits  rand_a
     2 bits  variant (0b10)
    62 bits  rand_b

The generator does not maintain monotonic counter state: it tolerates clock
rollback by construction (it simply reads the current time), and per
10.3.2 it never claims ordering beyond what the timestamp/random fields
themselves provide.
"""

from __future__ import annotations

import secrets
import time
import uuid

_VERSION_NIBBLE = 0x7
_VARIANT_BITS = 0b10
_TS_MS_BITS = 48
_RAND_A_BITS = 12
_RAND_B_BITS = 62
_TS_MS_MASK = (1 << _TS_MS_BITS) - 1


def uuid7() -> uuid.UUID:
    """Generate a new RFC 9562 UUIDv7 using a cryptographically secure RNG."""
    ts_ms = time.time_ns() // 1_000_000
    if ts_ms < 0:
        ts_ms = 0
    ts_ms &= _TS_MS_MASK

    rand_a = secrets.randbits(_RAND_A_BITS)
    rand_b = secrets.randbits(_RAND_B_BITS)

    value = ts_ms << 80
    value |= _VERSION_NIBBLE << 76
    value |= rand_a << 64
    value |= _VARIANT_BITS << 62
    value |= rand_b

    return uuid.UUID(int=value)


def uuid7_str() -> str:
    """Generate a new UUIDv7 in lowercase hyphenated canonical form."""
    return str(uuid7())


def is_uuid7(value: str) -> bool:
    """True if `value` is a syntactically valid, lowercase-canonical UUIDv7 string."""
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    if str(parsed) != value:
        return False
    return parsed.version == 7 and (parsed.variant == uuid.RFC_4122)
