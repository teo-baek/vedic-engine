"""Panchanga — the five daily limbs (tithi, nakshatra, yoga, karana) plus the Moon sign."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from jhora import utils
from jhora.panchanga import drik

import constants
from wrappers import _engine


def _name_from(table: Any, number: int) -> str | None:
    """1-based lookup into one of PyJHora's display-name tables."""
    try:
        return _engine.clean(table[number - 1])
    except (IndexError, TypeError):
        return None


def compute(
    moment: datetime,
    latitude: float,
    longitude: float,
    target_date: date | None = None,
) -> dict[str, Any]:
    """Panchanga at a given instant.

    ``target_date`` is evaluated at **00:00 UTC** of that date. The engine holds no timezone
    data, so choosing which UTC instant represents a user's local day is the caller's call —
    pass ``utc`` directly when you want an exact moment.
    """
    if target_date is not None:
        jd = _engine.date_to_julian_day(target_date)
        evaluated_at = datetime(
            target_date.year, target_date.month, target_date.day, tzinfo=moment.tzinfo
        )
    else:
        jd = _engine.to_julian_day(moment)
        evaluated_at = moment

    place = _engine.make_place(latitude, longitude)
    _engine.pin_ayanamsa()

    try:
        tithi = drik.tithi(jd, place)
        nakshatra = drik.nakshatra(jd, place)
        yogam = drik.yogam(jd, place)
        karana = drik.karana(jd, place)
        moon_sign = drik.raasi(jd, place)
    except Exception as exc:  # PyJHora raises bare exceptions
        raise _engine.CalculationError(f"panchanga failed: {exc}") from exc

    tithi_number = int(tithi[0])
    nakshatra_number = int(nakshatra[0])
    yoga_number = int(yogam[0])
    karana_number = int(karana[0])
    # ``raasi`` reports a 1-based sign number; the rest of this engine is 0-based.
    moon_sign_index = (int(moon_sign[0]) - 1) % 12

    return {
        "evaluated_at": evaluated_at.isoformat(),
        "tithi": {
            "number": tithi_number,
            "name": _name_from(utils.TITHI_LIST, tithi_number),
        },
        "nakshatra": {
            "number": nakshatra_number,
            "name": _engine.nakshatra_name(nakshatra_number),
            "pada": int(nakshatra[1]),
        },
        "yoga": {
            "number": yoga_number,
            "name": _name_from(utils.YOGAM_LIST, yoga_number),
        },
        "karana": {
            "number": karana_number,
            "name": _name_from(utils.KARANA_LIST, karana_number),
        },
        "moon_sign": {
            "sign": constants.SIGN_NAMES[moon_sign_index],
            "sign_index": moon_sign_index,
        },
    }
