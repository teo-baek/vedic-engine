"""Vimshottari dasha — the 120-year timeline keyed to the Moon's nakshatra.

Only ``vimsottari_mahadasa`` is taken from PyJHora. Its ``get_running_dhasa_for_given_date``
helper mutates module state on first call (later results shift by minutes depending on call
history), so the running mahadasha/antardasha are derived here by plain arithmetic instead:
antardashas divide their mahadasha in the canonical lord order, proportionally to each
lord's years out of 120. That subdivision *is* the Vimshottari definition — no astronomy is
involved beyond the mahadasha start instants themselves.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from jhora.horoscope.dhasa.graha import vimsottari

import constants
from wrappers import _engine

#: Canonical Vimshottari lord order (Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter,
#: Saturn, Mercury). Antardashas within a mahadasha start from the mahadasha lord and
#: follow this cycle.
_LORD_ORDER: tuple[int, ...] = (8, 5, 0, 1, 2, 7, 4, 6, 3)

_Period = tuple[int, float, float]  # (lord_id, start_jd, end_jd)


def _mahadasha_periods(jd: float, place: Any) -> list[_Period]:
    """Nine mahadashas as jd intervals.

    PyJHora returns start instants only, so each period ends where the next begins; the
    last one is closed with its own nominal length. The nine lengths sum to 120 years.
    """
    _engine.pin_ayanamsa()
    try:
        starts = vimsottari.vimsottari_mahadasa(jd, place)
    except Exception as exc:  # PyJHora raises bare exceptions
        raise _engine.CalculationError(f"vimshottari mahadasha failed: {exc}") from exc

    ordered = sorted(starts.items(), key=lambda item: item[1])
    periods: list[_Period] = []
    for index, (lord_id, start_jd) in enumerate(ordered):
        if index + 1 < len(ordered):
            end_jd = ordered[index + 1][1]
        else:
            end_jd = start_jd + constants.VIMSHOTTARI_YEARS[lord_id] * 365.25
        periods.append((int(lord_id), float(start_jd), float(end_jd)))
    return periods


def _running(periods: list[_Period], as_of_jd: float) -> tuple[_Period | None, _Period | None]:
    """The mahadasha and antardasha containing ``as_of_jd``, or ``(None, None)``.

    ``None`` is a real answer, not a failure: an ``as_of`` before the first period or after
    the 120-year cycle simply has no running period.
    """
    maha = next((p for p in periods if p[1] <= as_of_jd < p[2]), None)
    if maha is None:
        return None, None

    lord, start, end = maha
    span = end - start
    cursor = start
    first = _LORD_ORDER.index(lord)
    for offset in range(9):
        sub_lord = _LORD_ORDER[(first + offset) % 9]
        share = constants.VIMSHOTTARI_YEARS[sub_lord] / constants.DASHA_CYCLE_YEARS
        sub_end = cursor + span * share
        if cursor <= as_of_jd < sub_end:
            return maha, (sub_lord, cursor, sub_end)
        cursor = sub_end
    return maha, None  # float rounding at the very edge of the mahadasha


def _iso(jd: float) -> str:
    return _engine.julian_day_to_datetime(jd).isoformat()


def compute(
    moment: datetime, latitude: float, longitude: float, as_of: datetime | None = None
) -> dict[str, Any]:
    """Full mahadasha timeline plus the period running at ``as_of``.

    ``as_of`` defaults to the current instant. Pass it explicitly for reproducible output —
    every value in the response is otherwise a pure function of the birth data.
    """
    jd = _engine.to_julian_day(moment)
    place = _engine.make_place(latitude, longitude)
    reference = (as_of or datetime.now(UTC)).astimezone(UTC)

    periods = _mahadasha_periods(jd, place)
    maha, antara = _running(periods, _engine.to_julian_day(reference))

    return {
        "system": constants.DASHA_SYSTEM,
        "cycle_years": constants.DASHA_CYCLE_YEARS,
        "as_of": reference.isoformat(),
        "periods": [
            {
                "lord_id": lord,
                "lord": constants.PLANET_NAMES[lord],
                "years": constants.VIMSHOTTARI_YEARS[lord],
                "start": _iso(start),
                "end": _iso(end),
            }
            for lord, start, end in periods
        ],
        "current": {
            "lord": constants.PLANET_NAMES[maha[0]] if maha else None,
            "start": _iso(maha[1]) if maha else None,
            "end": _iso(maha[2]) if maha else None,
            "sub_lord": constants.PLANET_NAMES[antara[0]] if antara else None,
            "sub_start": _iso(antara[1]) if antara else None,
            "sub_end": _iso(antara[2]) if antara else None,
        },
    }
