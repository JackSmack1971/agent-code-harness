from __future__ import annotations

import time
import uuid
from unittest import mock

from hypothesis import given, settings
from hypothesis import strategies as st

from agentic_harness._identity import is_uuid7, uuid7, uuid7_str


def test_generated_value_has_version_7() -> None:
    for _ in range(200):
        assert uuid7().version == 7


def test_generated_value_has_rfc_4122_variant() -> None:
    for _ in range(200):
        assert uuid7().variant == uuid.RFC_4122


def test_generated_value_is_syntactically_a_uuid() -> None:
    value = uuid7()
    assert isinstance(value, uuid.UUID)


def test_string_form_is_lowercase_hyphenated() -> None:
    text = uuid7_str()
    assert text == text.lower()
    parts = text.split("-")
    assert [len(p) for p in parts] == [8, 4, 4, 4, 12]


def test_is_uuid7_accepts_generated_values() -> None:
    for _ in range(50):
        assert is_uuid7(uuid7_str())


def test_is_uuid7_rejects_uuid4() -> None:
    assert not is_uuid7(str(uuid.uuid4()))


def test_is_uuid7_rejects_uppercase() -> None:
    text = uuid7_str()
    assert not is_uuid7(text.upper())


def test_is_uuid7_rejects_malformed_strings() -> None:
    for bad in ("", "not-a-uuid", "01911f2e-7abc-7def-8abc", "01911f2e7abc7def8abc0123456789ab"):
        assert not is_uuid7(bad)


def test_no_two_generated_values_collide() -> None:
    values = {uuid7() for _ in range(5000)}
    assert len(values) == 5000


def test_timestamp_field_is_non_decreasing_across_generations_absent_clock_change() -> None:
    previous_ts = None
    for _ in range(200):
        value = uuid7()
        ts_ms = value.int >> 80
        if previous_ts is not None:
            assert ts_ms >= previous_ts
        previous_ts = ts_ms


def test_tolerates_clock_rollback_without_raising_or_producing_a_malformed_uuid() -> None:
    real_time_ns = time.time_ns
    with mock.patch("agentic_harness._identity.time.time_ns", return_value=real_time_ns() - 3_600_000_000_000):
        value = uuid7()
    assert value.version == 7
    assert value.variant == uuid.RFC_4122


def test_does_not_claim_monotonic_ordering_beyond_timestamp_precision() -> None:
    """Two UUIDv7s minted within the same millisecond may sort in either
    order; only the millisecond timestamp field itself is ordered.
    """
    real_time_ns = time.time_ns()
    with mock.patch("agentic_harness._identity.time.time_ns", return_value=real_time_ns):
        a = uuid7()
        b = uuid7()
    assert (a.int >> 80) == (b.int >> 80)


@given(offset_ms=st.integers(min_value=-10**15, max_value=10**15))
@settings(max_examples=100)
def test_property_generation_never_raises_regardless_of_clock_value(offset_ms: int) -> None:
    base_ns = time.time_ns() + offset_ms * 1_000_000
    with mock.patch("agentic_harness._identity.time.time_ns", return_value=base_ns):
        value = uuid7()
    assert value.version == 7
    assert value.variant == uuid.RFC_4122
