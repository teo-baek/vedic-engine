"""D1 (rasi) and D9 (navamsa) positions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import constants
from wrappers import _engine


def _planet_entry(
    planet_id: int, sign: int, degree: float, ascendant_sign: int, retrograde: bool
) -> dict[str, Any]:
    return {
        "id": planet_id,
        "name": constants.PLANET_NAMES[planet_id],
        "sign": _engine.sign_name(sign),
        "sign_index": sign,
        "house": _engine.whole_sign_house(sign, ascendant_sign),
        "degree": round(degree, 6),
        "retrograde": retrograde,
    }


def compute(moment: datetime, latitude: float, longitude: float) -> dict[str, Any]:
    """Rasi chart plus the navamsa divisional chart.

    Nodes (Rahu/Ketu) are always retrograde by definition; PyJHora reports true motion, so
    whatever it says is passed through unchanged rather than being overridden here.
    """
    jd = _engine.to_julian_day(moment)
    place = _engine.make_place(latitude, longitude)

    rasi_rows = _engine.rasi_chart(jd, place)
    (asc_sign, asc_degree), planets = _engine.split_chart(rasi_rows)
    retrograde = _engine.retrograde_planet_ids(jd, place)

    navamsa_rows = _engine.divisional_chart(jd, place, factor=9)
    (nav_asc_sign, nav_asc_degree), nav_planets = _engine.split_chart(navamsa_rows)

    return {
        "ascendant": {
            "sign": _engine.sign_name(asc_sign),
            "sign_index": asc_sign,
            "degree": round(asc_degree, 6),
        },
        "planets": [
            _planet_entry(pid, sign, degree, asc_sign, pid in retrograde)
            for pid, sign, degree in planets
        ],
        "navamsa": {
            "ascendant": {
                "sign": _engine.sign_name(nav_asc_sign),
                "sign_index": nav_asc_sign,
                "degree": round(nav_asc_degree, 6),
            },
            "planets": [
                _planet_entry(pid, sign, degree, nav_asc_sign, pid in retrograde)
                for pid, sign, degree in nav_planets
            ],
        },
    }
