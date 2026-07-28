"""Yogas — planetary combinations that PyJHora detects in a chart.

**Every** detected yoga is returned. Deciding which ones are worth showing a reader is a
product judgement and belongs to the caller, not to this engine.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from jhora.horoscope.chart import yoga as jhora_yoga

from wrappers import _engine


def compute(moment: datetime, latitude: float, longitude: float) -> dict[str, Any]:
    """Detected yogas with their Sanskrit keys, definitions and classical effects.

    ``planets_involved`` and ``strength`` are part of the response shape but are always
    empty/``null``: PyJHora's yoga API reports presence only. Reconstructing participants
    would mean re-implementing all 284 yoga definitions, which is out of scope for a
    wrapper. Callers rank yogas by their own curated priority list instead.
    """
    jd = _engine.to_julian_day(moment)
    place = _engine.make_place(latitude, longitude)

    _engine.pin_ayanamsa()
    try:
        detected, detected_count, checked_count = jhora_yoga.get_yoga_details(jd, place)
    except Exception as exc:  # PyJHora raises bare exceptions
        raise _engine.CalculationError(f"yoga detection failed: {exc}") from exc

    yogas: list[dict[str, Any]] = []
    for key, detail in detected.items():
        chart_code, name, definition, effect = (list(detail) + [None] * 4)[:4]
        yogas.append(
            {
                "key": key,
                "name": name,
                "chart": chart_code,
                "definition": definition,
                "effect": effect,
                "planets_involved": [],
                "strength": None,
            }
        )
    yogas.sort(key=lambda item: item["key"])

    return {
        "yogas": yogas,
        "detected_count": int(detected_count),
        "checked_count": int(checked_count),
    }
