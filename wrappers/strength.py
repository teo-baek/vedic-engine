"""Shadbala — the six-fold planetary strength, normalised to a 0-100 scale."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from jhora.horoscope.chart import strength as jhora_strength

import constants
from wrappers import _engine

#: Row indices inside PyJHora's ``shad_bala`` return list.
_ROW_TOTAL_SHASHTIAMSA = 6
_ROW_RUPAS = 7
_ROW_RATIO = 8

#: A planet meeting its classical minimum (ratio 1.0) scores 50; twice the minimum caps at 100.
_RATIO_TO_SCORE = 50.0


def compute(moment: datetime, latitude: float, longitude: float) -> dict[str, Any]:
    """Strength of the seven classical planets.

    ``score_100`` is a plain unit conversion of PyJHora's strength ratio (achieved rupas /
    classically required rupas), not an interpretation: 1.0 -> 50, 2.0 and above -> 100.
    The raw ``rupas`` and ``ratio`` are returned alongside so callers can re-derive their
    own scale without recomputing the chart.
    """
    jd = _engine.to_julian_day(moment)
    place = _engine.make_place(latitude, longitude)

    _engine.pin_ayanamsa()
    try:
        rows = jhora_strength.shad_bala(jd, place)
    except Exception as exc:  # PyJHora raises bare exceptions
        raise _engine.CalculationError(f"shadbala failed: {exc}") from exc

    if len(rows) <= _ROW_RATIO:
        raise _engine.CalculationError("shadbala returned an unexpected shape")

    totals = rows[_ROW_TOTAL_SHASHTIAMSA]
    rupas = rows[_ROW_RUPAS]
    ratios = rows[_ROW_RATIO]

    planets: list[dict[str, Any]] = []
    for planet_id in constants.SHADBALA_PLANETS:
        ratio = float(ratios[planet_id])
        planets.append(
            {
                "id": planet_id,
                "name": constants.PLANET_NAMES[planet_id],
                "score_100": round(min(ratio * _RATIO_TO_SCORE, 100.0), 2),
                "ratio": round(ratio, 4),
                "rupas": round(float(rupas[planet_id]), 4),
                "shashtiamsas": round(float(totals[planet_id]), 2),
            }
        )

    for rank, planet in enumerate(sorted(planets, key=lambda p: p["rupas"], reverse=True), 1):
        planet["rank"] = rank

    return {"planets": planets}
