from __future__ import annotations

import datetime as _dt
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml
from hypothesis import given
from hypothesis import strategies as st

from agentic_harness._canonical import (
    CanonicalizationError,
    canonical_json_bytes,
    digest_for,
    format_datetime,
    format_decimal,
    parse_untrusted_json,
    to_canonical_value,
)
from _canonical_reference_impl import (
    ReferenceCanonicalizationError,
    reference_canonical_json_bytes,
    reference_digest_for,
)


def _contract(contracts_root: Path) -> dict[str, Any]:
    return yaml.safe_load((contracts_root / "canonical_serialization.yaml").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Golden vectors (9.5.5 / 10.4.5): frozen bytes/digests, cross-checked by an
# independently written second encoder.
# ---------------------------------------------------------------------------


def _golden_case_ids(contracts_root: Path) -> list[str]:
    return [v["name"] for v in _contract(contracts_root)["golden_vectors"]]


@pytest.mark.parametrize("index", range(4))
def test_golden_vector_bytes_and_digest_match_contract(contracts_root: Path, index: int) -> None:
    vector = _contract(contracts_root)["golden_vectors"][index]
    assert vector["canonical_json"].encode("utf-8")
    computed_bytes = vector["canonical_json"].encode("utf-8")
    import hashlib

    assert "sha256:" + hashlib.sha256(computed_bytes).hexdigest() == vector["digest"]


def test_empty_object_golden_vector() -> None:
    assert canonical_json_bytes({}) == b"{}"
    assert digest_for({}) == "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"


def test_simple_scalars_golden_vector() -> None:
    value = {"a": 1, "b": True}
    assert canonical_json_bytes(value) == b'{"a":1,"b":true}'
    assert digest_for(value) == "sha256:d918e8d1a9eb1f54b583326cad9950c771474b5c8ac1072bb0f2a0ad148d6de5"


def test_unicode_null_array_golden_vector() -> None:
    value = {"name": "café", "none": None, "tags": ["a", "b"]}
    assert canonical_json_bytes(value) == '{"name":"café","none":null,"tags":["a","b"]}'.encode("utf-8")
    assert digest_for(value) == "sha256:ae302866dc4eabd91aac60b6a6e2e5ed315ff7bf2377da9cd00aa1356c211e49"


def test_decimal_uuid_timestamp_golden_vector_frozen_after_cross_check() -> None:
    value = {
        "decimal": Decimal("1.23"),
        "id": uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        "ts": _dt.datetime(2026, 9, 19, 3, 38, 0, tzinfo=_dt.timezone.utc),
    }
    expected_bytes = b'{"decimal":"1.23","id":"550e8400-e29b-41d4-a716-446655440000","ts":"2026-09-19T03:38:00Z"}'
    assert canonical_json_bytes(value) == expected_bytes
    assert reference_canonical_json_bytes(value) == expected_bytes
    expected_digest = "sha256:d40caf42471b7c20c1c9c41116add7380836220b4392d5d99edb442bc1c737d7"
    assert digest_for(value) == expected_digest
    assert reference_digest_for(value) == expected_digest


def test_golden_vectors_are_flagged_frozen(contracts_root: Path) -> None:
    for vector in _contract(contracts_root)["golden_vectors"]:
        assert vector["frozen"] is True


def test_fourth_vector_records_its_cross_checking_implementations(contracts_root: Path) -> None:
    vectors = _contract(contracts_root)["golden_vectors"]
    fourth = vectors[3]
    assert len(fourth["cross_checked_by"]) >= 2


# ---------------------------------------------------------------------------
# Cross-implementation agreement (9.5.6): the primary serializer and an
# independent fixture implementation must agree byte-for-byte.
# ---------------------------------------------------------------------------

_CROSS_CHECK_VALUES: list[Any] = [
    {},
    {"a": 1, "b": True},
    {"name": "café", "none": None, "tags": ["a", "b"]},
    {"nested": {"z": 1, "a": 2}, "list": [3, 2, 1], "set": {3, 1, 2}},
    {"decimal": Decimal("-0"), "big": Decimal("123456789012345678901234567890.00010")},
    {"empty_array": [], "empty_object": {}},
    {"nested_sets": {frozenset({1, 2}), frozenset({3})}},
    {"control": "line1\nline2\ttab\"quote\\back/slash  "},
    {"composed": "é", "decomposed": "é"},
]


@pytest.mark.parametrize("value", _CROSS_CHECK_VALUES, ids=range(len(_CROSS_CHECK_VALUES)))
def test_primary_and_independent_implementations_agree_byte_for_byte(value: Any) -> None:
    assert canonical_json_bytes(value) == reference_canonical_json_bytes(value)
    assert digest_for(value) == reference_digest_for(value)


# ---------------------------------------------------------------------------
# Required property/conformance tests (9.5.6).
# ---------------------------------------------------------------------------


def test_dictionary_insertion_order_does_not_affect_bytes() -> None:
    a = {"z": 1, "a": 2, "m": 3}
    b = {"a": 2, "m": 3, "z": 1}
    assert canonical_json_bytes(a) == canonical_json_bytes(b)


def test_set_iteration_order_does_not_affect_bytes() -> None:
    a = frozenset({"z", "a", "m"})
    b = frozenset({"m", "z", "a"})
    assert canonical_json_bytes(a) == canonical_json_bytes(b)


def test_omitted_and_null_differ() -> None:
    with_null = {"x": None}
    without_key: dict[str, Any] = {}
    assert canonical_json_bytes(with_null) != canonical_json_bytes(without_key)
    assert canonical_json_bytes(with_null) == b'{"x":null}'
    assert canonical_json_bytes(without_key) == b"{}"


def test_float_input_is_rejected() -> None:
    with pytest.raises(CanonicalizationError):
        to_canonical_value(1.5)
    with pytest.raises(ReferenceCanonicalizationError):
        reference_canonical_json_bytes(1.5)


def test_equivalent_timezone_offsets_normalize_to_one_utc_representation() -> None:
    utc = _dt.datetime(2026, 9, 19, 3, 38, 0, tzinfo=_dt.timezone.utc)
    plus_two = _dt.datetime(2026, 9, 19, 5, 38, 0, tzinfo=_dt.timezone(_dt.timedelta(hours=2)))
    minus_five = _dt.datetime(2026, 9, 18, 22, 38, 0, tzinfo=_dt.timezone(_dt.timedelta(hours=-5)))
    assert format_datetime(utc) == format_datetime(plus_two) == format_datetime(minus_five)
    assert format_datetime(utc) == "2026-09-19T03:38:00Z"


def test_decimal_spelling_differences_normalize_identically_where_numerically_equal() -> None:
    assert format_decimal(Decimal("1.230")) == format_decimal(Decimal("1.23"))
    assert format_decimal(Decimal("1.230")) == "1.23"
    assert format_decimal(Decimal("0.0")) == "0"
    assert format_decimal(Decimal("-0")) == "0"
    assert format_decimal(Decimal("1E+2")) == "100"
    assert format_decimal(Decimal("1E+2")) == format_decimal(Decimal("100"))


# ---------------------------------------------------------------------------
# 10.4.5 required edge-case coverage, fail-closed.
# ---------------------------------------------------------------------------


def test_control_characters_backslash_quote_and_solidus_escaping() -> None:
    value = {"s": 'line1\nline2\ttab"quote\\back/slash'}
    encoded = canonical_json_bytes(value).decode("utf-8")
    assert '\\n' in encoded
    assert '\\t' in encoded
    assert '\\"' in encoded
    assert "\\\\" in encoded
    # '/' is not gratuitously escaped.
    assert "back/slash" in encoded


def test_u2028_u2029_are_not_gratuitously_escaped() -> None:
    value = {"s": "  "}
    encoded = canonical_json_bytes(value)
    assert "  ".encode("utf-8") in encoded


def test_composed_and_decomposed_unicode_remain_distinct_identities() -> None:
    composed = {"s": "é"}  # é as a single code point
    decomposed = {"s": "é"}  # e + combining acute accent
    assert canonical_json_bytes(composed) != canonical_json_bytes(decomposed)


def test_very_large_decimal_magnitude_and_scale() -> None:
    huge = Decimal("1" + "0" * 150)
    tiny = Decimal("0." + "0" * 150 + "1")
    assert format_decimal(huge) == "1" + "0" * 150
    assert format_decimal(tiny) == "0." + "0" * 150 + "1"


def test_signed_zero_canonicalizes_to_bare_zero() -> None:
    assert format_decimal(Decimal("-0")) == "0"
    assert format_decimal(Decimal("-0.00")) == "0"


def test_empty_containers() -> None:
    assert canonical_json_bytes({"a": [], "b": {}}) == b'{"a":[],"b":{}}'


def test_nested_sets() -> None:
    value = {"outer": {frozenset({1, 2}), frozenset({3})}}
    encoded = canonical_json_bytes(value)
    assert encoded == reference_canonical_json_bytes(value)


def test_invalid_surrogate_input_is_rejected() -> None:
    lone_surrogate = "\ud800"
    with pytest.raises(CanonicalizationError):
        to_canonical_value({"s": lone_surrogate})


def test_bytes_are_forbidden() -> None:
    with pytest.raises(CanonicalizationError):
        to_canonical_value(b"raw bytes")


def test_decimal_nan_and_infinite_are_rejected() -> None:
    for bad in (Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity")):
        with pytest.raises(CanonicalizationError):
            to_canonical_value(bad)


def test_decimal_digit_count_limit_is_enforced_not_truncated() -> None:
    over_limit = Decimal("1" * 201)
    with pytest.raises(CanonicalizationError):
        to_canonical_value(over_limit)
    within_limit = Decimal("1" * 200)
    assert to_canonical_value(within_limit) == "1" * 200


def test_naive_datetime_is_rejected() -> None:
    naive = _dt.datetime(2026, 9, 19, 3, 38, 0)
    with pytest.raises(CanonicalizationError):
        to_canonical_value(naive)


def test_duplicate_object_key_in_untrusted_json_is_rejected() -> None:
    with pytest.raises(CanonicalizationError):
        parse_untrusted_json('{"a":1,"a":2}')


def test_unsupported_type_is_rejected() -> None:
    class Unsupported:
        pass

    with pytest.raises(CanonicalizationError):
        to_canonical_value(Unsupported())


def test_reason_code_is_registered(contracts_root: Path) -> None:
    registry = yaml.safe_load((contracts_root / "reason_code_registry.yaml").read_text(encoding="utf-8"))
    codes = {c["code"] for c in registry["codes"]}
    try:
        to_canonical_value(1.5)
    except CanonicalizationError as exc:
        assert exc.reason_code in codes
    else:  # pragma: no cover
        pytest.fail("expected CanonicalizationError")


# ---------------------------------------------------------------------------
# Combinatorial property tests (canonicalization invariants).
# ---------------------------------------------------------------------------

_json_safe_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), min_codepoint=0x20, max_codepoint=0x2FFF),
    max_size=20,
)
_scalar = st.one_of(st.none(), st.booleans(), st.integers(min_value=-(10**9), max_value=10**9), _json_safe_text)
_json_value = st.recursive(
    _scalar,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(_json_safe_text.filter(lambda s: len(s) > 0), children, max_size=4),
    ),
    max_leaves=12,
)


@given(_json_value)
def test_property_primary_matches_reference_implementation(value: Any) -> None:
    assert canonical_json_bytes(value) == reference_canonical_json_bytes(value)


@given(st.dictionaries(_json_safe_text.filter(lambda s: len(s) > 0), _scalar, max_size=6))
def test_property_key_insertion_order_is_irrelevant(mapping: dict[str, Any]) -> None:
    items = list(mapping.items())
    shuffled = dict(reversed(items))
    assert canonical_json_bytes(mapping) == canonical_json_bytes(shuffled)
