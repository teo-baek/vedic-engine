"""Golden regression — frozen output for five reference births.

These files are the contract with the calling backend. A diff here means either a genuine
fix (bump ``ENGINE_VERSION`` and regenerate with ``make golden``) or an accident. Never
regenerate to make a red test green without reading the diff first: cached charts on the
caller's side were produced by the old numbers.
"""

from __future__ import annotations

from conftest import AS_OF, BIRTHS_BY_KEY, Birth, load_golden

from wrappers import chart, compat, dasha, panchanga, strength, yoga

_PARTNER = BIRTHS_BY_KEY["busan_1978"]


def test_chart_is_frozen(birth: Birth) -> None:
    assert chart.compute(birth.utc, birth.lat, birth.lon) == load_golden(birth.key)["chart"]


def test_dasha_is_frozen(birth: Birth) -> None:
    actual = dasha.compute(birth.utc, birth.lat, birth.lon, as_of=AS_OF)
    assert actual == load_golden(birth.key)["dasha"]


def test_panchanga_is_frozen(birth: Birth) -> None:
    actual = panchanga.compute(birth.utc, birth.lat, birth.lon)
    assert actual == load_golden(birth.key)["panchanga"]


def test_strength_is_frozen(birth: Birth) -> None:
    actual = strength.compute(birth.utc, birth.lat, birth.lon)
    assert actual == load_golden(birth.key)["strength"]


def test_compat_against_common_partner_is_frozen(birth: Birth) -> None:
    actual = compat.compute(
        birth.utc, birth.lat, birth.lon, _PARTNER.utc, _PARTNER.lat, _PARTNER.lon
    )
    assert actual == load_golden(birth.key)["compat_vs_busan_1978"]


def test_yoga_keys_are_frozen(birth: Birth) -> None:
    """Yoga *descriptions* are upstream prose; only the detected set is contractual."""
    actual = yoga.compute(birth.utc, birth.lat, birth.lon)
    expected = load_golden(birth.key)["yoga"]
    assert [item["key"] for item in actual["yogas"]] == expected["keys"]
    assert actual["detected_count"] == expected["detected_count"]
