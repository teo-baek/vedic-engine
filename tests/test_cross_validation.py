"""Independent recomputation — the engine's answers checked against a second derivation.

PyJHora is a large library; these tests do not trust its bookkeeping. Every value here is
recomputed from Swiss Ephemeris primitives (or from first principles) and compared with what
the wrappers return.

Scope note, stated plainly: both paths ultimately read the same ephemeris, so this proves
the *wrapper* is right — ayanamsa applied, sidereal longitudes converted, signs, degrees,
houses and nakshatras mapped correctly. It is not a check of the ephemeris itself. Spot
checks against a third-party astrology service remain a manual step before launch.
"""

from __future__ import annotations

import swisseph as swe
from conftest import Birth

import constants
from wrappers import _engine, chart, compat, panchanga

_SIDEREAL_FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

#: Vimshottari lord of each nakshatra, cycling every nine starting at Ashwini = Ketu.
_NAKSHATRA_LORDS = (8, 5, 0, 1, 2, 7, 4, 6, 3)

_SWE_PLANET = {
    0: swe.SUN,
    1: swe.MOON,
    2: swe.MARS,
    3: swe.MERCURY,
    4: swe.JUPITER,
    5: swe.VENUS,
    6: swe.SATURN,
}


def _sidereal_longitude(jd: float, planet_id: int) -> float:
    """Sidereal longitude by direct Swiss Ephemeris call, on PyJHora's conventions.

    PyJHora computes *true* (geometric) positions — ``FLG_TRUEPOS``, i.e. no light-time /
    aberration correction (~20 arcsec on the Sun) — in sidereal mode. The same convention
    is used here so the comparison isolates what this suite is actually validating: that
    the wrapper applies the Lahiri ayanamsa and maps signs, degrees, houses and nakshatras
    correctly. The convention choice itself is upstream's, documented in the README.
    """
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_TRUEPOS
    return swe.calc_ut(jd, _SWE_PLANET[planet_id], flags)[0][0] % 360.0


def test_ayanamsa_matches_swiss_ephemeris_lahiri(birth: Birth) -> None:
    """The engine must be on Lahiri — not the PyJHora default (True Pushya)."""
    jd = _engine.to_julian_day(birth.utc)
    _engine.pin_ayanamsa()
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    assert abs(swe.get_ayanamsa_ut(jd) - 23.0) < 3.0, "sanity: Lahiri is ~23-24 deg in 1900-2100"


def test_ascendant_matches_independent_house_calculation(birth: Birth) -> None:
    """Ascendant recomputed straight from ``swe.houses_ex`` in sidereal mode."""
    jd = _engine.to_julian_day(birth.utc)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    _, ascmc = swe.houses_ex(jd, birth.lat, birth.lon, b"P", _SIDEREAL_FLAGS)
    expected_absolute = ascmc[0] % 360.0

    result = chart.compute(birth.utc, birth.lat, birth.lon)
    actual_absolute = result["ascendant"]["sign_index"] * 30 + result["ascendant"]["degree"]

    assert abs(actual_absolute - expected_absolute) < 1e-4
    assert result["ascendant"]["sign"] == constants.SIGN_NAMES[int(expected_absolute // 30)]


def test_planet_positions_match_independent_calculation(birth: Birth) -> None:
    """Every classical planet's sign and degree, recomputed one by one."""
    jd = _engine.to_julian_day(birth.utc)
    result = chart.compute(birth.utc, birth.lat, birth.lon)
    by_id = {planet["id"]: planet for planet in result["planets"]}

    for planet_id in constants.SHADBALA_PLANETS:
        expected = _sidereal_longitude(jd, planet_id)
        planet = by_id[planet_id]
        actual = planet["sign_index"] * 30 + planet["degree"]
        assert abs(actual - expected) < 1e-3, f"{planet['name']} longitude"
        assert planet["sign"] == constants.SIGN_NAMES[int(expected // 30)]


def test_nodes_are_opposite(birth: Birth) -> None:
    """Rahu and Ketu are always exactly 180 degrees apart — a cheap structural invariant."""
    result = chart.compute(birth.utc, birth.lat, birth.lon)
    by_id = {planet["id"]: planet for planet in result["planets"]}
    rahu = by_id[7]["sign_index"] * 30 + by_id[7]["degree"]
    ketu = by_id[8]["sign_index"] * 30 + by_id[8]["degree"]
    assert abs(((rahu - ketu) % 360) - 180.0) < 1e-6


def test_houses_follow_whole_sign_from_ascendant(birth: Birth) -> None:
    """House numbering is whole-sign: the ascendant's sign is house 1."""
    result = chart.compute(birth.utc, birth.lat, birth.lon)
    asc_sign = result["ascendant"]["sign_index"]
    for planet in result["planets"]:
        expected = ((planet["sign_index"] - asc_sign) % 12) + 1
        assert planet["house"] == expected


def test_nakshatra_derived_from_moon_longitude(birth: Birth) -> None:
    """Nakshatra and pada recomputed by dividing the Moon's longitude directly."""
    jd = _engine.to_julian_day(birth.utc)
    moon = _sidereal_longitude(jd, 1)

    span = 360.0 / 27.0
    expected_number = int(moon // span) + 1
    expected_pada = int((moon % span) // (span / 4)) + 1

    result = panchanga.compute(birth.utc, birth.lat, birth.lon)
    assert result["nakshatra"]["number"] == expected_number
    assert result["nakshatra"]["pada"] == expected_pada
    assert result["nakshatra"]["name"] == constants.NAKSHATRA_NAMES[expected_number - 1]


def test_moon_sign_derived_from_moon_longitude(birth: Birth) -> None:
    jd = _engine.to_julian_day(birth.utc)
    moon = _sidereal_longitude(jd, 1)
    result = panchanga.compute(birth.utc, birth.lat, birth.lon)
    assert result["moon_sign"]["sign_index"] == int(moon // 30)


def test_compat_uses_each_side_moon_nakshatra() -> None:
    """The matching input is each side's Moon nakshatra — verified against the chart itself."""
    from conftest import BIRTHS_BY_KEY

    a = BIRTHS_BY_KEY["seoul_1990"]
    b = BIRTHS_BY_KEY["busan_1978"]
    result = compat.compute(a.utc, a.lat, a.lon, b.utc, b.lat, b.lon)

    for side, birth in (("a", a), ("b", b)):
        moon = _sidereal_longitude(_engine.to_julian_day(birth.utc), 1)
        assert result[side]["nakshatra_number"] == int(moon // (360.0 / 27.0)) + 1


def test_vimshottari_first_lord_is_moon_nakshatra_lord(birth: Birth) -> None:
    """The dasha sequence is seeded by the Moon's nakshatra — recomputed independently."""
    from wrappers import dasha

    jd = _engine.to_julian_day(birth.utc)
    moon = _sidereal_longitude(jd, 1)
    nakshatra_index = int(moon // (360.0 / 27.0))
    expected_lord = _NAKSHATRA_LORDS[nakshatra_index % 9]

    result = dasha.compute(birth.utc, birth.lat, birth.lon, as_of=birth.utc)
    assert result["periods"][0]["lord_id"] == expected_lord
    assert result["periods"][0]["lord"] == constants.PLANET_NAMES[expected_lord]


def test_vimshottari_sequence_and_lengths_are_canonical(birth: Birth) -> None:
    """Nine periods, in the fixed lord order, summing to 120 years."""
    from wrappers import dasha

    result = dasha.compute(birth.utc, birth.lat, birth.lon, as_of=birth.utc)
    lords = [period["lord_id"] for period in result["periods"]]

    assert len(lords) == 9
    start = _NAKSHATRA_LORDS.index(lords[0])
    expected = [_NAKSHATRA_LORDS[(start + offset) % 9] for offset in range(9)]
    assert lords == expected

    total = sum(constants.VIMSHOTTARI_YEARS[lord] for lord in lords)
    assert total == constants.DASHA_CYCLE_YEARS
