"""Ashtakoota matching — the eight kutas that sum to 36 points."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from jhora.horoscope.match import compatibility
from jhora.panchanga import drik

import constants
from wrappers import _engine

_MAX_POINTS = sum(points for _, points in constants.ASHTAKOOTA_MAX)


def _moon_nakshatra(moment: datetime, latitude: float, longitude: float) -> tuple[int, int]:
    """``(nakshatra_number, pada)`` — both 1-based, as the matching tables expect."""
    jd = _engine.to_julian_day(moment)
    place = _engine.make_place(latitude, longitude)
    _engine.pin_ayanamsa()
    try:
        nakshatra = drik.nakshatra(jd, place)
    except Exception as exc:  # PyJHora raises bare exceptions
        raise _engine.CalculationError(f"nakshatra lookup failed: {exc}") from exc
    return int(nakshatra[0]), int(nakshatra[1])


def compute(
    a_moment: datetime,
    a_latitude: float,
    a_longitude: float,
    b_moment: datetime,
    b_latitude: float,
    b_longitude: float,
) -> dict[str, Any]:
    """Ashtakoota score for two birth points.

    PyJHora names the two sides "boy" and "girl" because the classical tables are asymmetric
    — several kutas are counted *from* one side. This engine keeps the API neutral: ``a`` is
    passed as the first side and ``b`` as the second, and swapping them can change the score.
    That asymmetry is inherent to the system, not an artefact of this wrapper.
    """
    a_nakshatra, a_pada = _moon_nakshatra(a_moment, a_latitude, a_longitude)
    b_nakshatra, b_pada = _moon_nakshatra(b_moment, b_latitude, b_longitude)

    try:
        koota = compatibility.Ashtakoota(
            boy_nakshatra_number=a_nakshatra,
            boy_paadham_number=a_pada,
            girl_nakshatra_number=b_nakshatra,
            girl_paadham_number=b_pada,
            method="North",
        )
        result = koota.compatibility_score()
    except Exception as exc:  # PyJHora raises bare exceptions
        raise _engine.CalculationError(f"ashtakoota failed: {exc}") from exc

    details: list[dict[str, Any]] = []
    for kuta, max_points in constants.ASHTAKOOTA_MAX:
        points = float(result[constants.ASHTAKOOTA_RESULT_INDEX[kuta]])
        details.append(
            {
                "kuta": kuta,
                "points": points,
                "max_points": max_points,
                "matched": points > 0,
            }
        )

    supplementary = {
        name: bool(result[index])
        for name, index in constants.SUPPLEMENTARY_PORUTHAM_INDEX.items()
    }

    porutham_36 = float(result[constants.ASHTAKOOTA_TOTAL_INDEX])
    return {
        "porutham_36": porutham_36,
        "max_porutham": _MAX_POINTS,
        "score_100": round(porutham_36 / _MAX_POINTS * 100, 2),
        "details": details,
        "supplementary": supplementary,
        "a": {"nakshatra_number": a_nakshatra, "nakshatra": _engine.nakshatra_name(a_nakshatra),
              "pada": a_pada},
        "b": {"nakshatra_number": b_nakshatra, "nakshatra": _engine.nakshatra_name(b_nakshatra),
              "pada": b_pada},
    }
