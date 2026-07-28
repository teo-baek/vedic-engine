"""Shared PyJHora plumbing — Julian day conversion, place construction, chart parsing.

PyJHora keeps its ayanamsa setting in process-wide mutable state. This module pins it to
Lahiri at import time and re-pins it before every calculation, so no request can observe a
setting another request left behind.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from jhora import utils
from jhora.horoscope.chart import charts
from jhora.panchanga import drik

import constants


class CalculationError(RuntimeError):
    """PyJHora failed to produce a result for otherwise valid input."""


def pin_ayanamsa() -> None:
    """Force Lahiri. Cheap, idempotent, and called before every calculation."""
    drik.set_ayanamsa_mode(constants.AYANAMSA_MODE)


pin_ayanamsa()


def to_julian_day(moment: datetime) -> float:
    """UTC instant -> Julian day.

    The caller has already resolved the birthplace's timezone, so the instant is absolute.
    Places are built with a zero UTC offset (see :func:`make_place`), which keeps PyJHora's
    internal "local time" identical to UTC and removes timezone handling from this service.
    """
    if moment.tzinfo is None:
        raise ValueError("moment must be timezone-aware and in UTC")
    moment = moment.astimezone(UTC)
    seconds = moment.second + moment.microsecond / 1_000_000
    return utils.julian_day_number(
        drik.Date(moment.year, moment.month, moment.day),
        (moment.hour, moment.minute, seconds),
    )


def date_to_julian_day(day: date) -> float:
    """Calendar date -> Julian day at 00:00 UTC."""
    return utils.julian_day_number(drik.Date(day.year, day.month, day.day), (0, 0, 0))


def julian_day_to_datetime(jd: float) -> datetime:
    """Julian day -> UTC datetime, rounded to the second."""
    year, month, day, hours = utils.jd_to_gregorian(jd)
    total_seconds = round(hours * 3600)
    # A rounded 24:00:00 belongs to the next day; let timedelta normalise it.
    from datetime import timedelta

    return datetime(year, month, day, tzinfo=UTC) + timedelta(seconds=total_seconds)


def make_place(latitude: float, longitude: float) -> drik.Place:
    """Build a PyJHora place with a **zero** UTC offset — the engine knows no timezones."""
    return drik.Place("", float(latitude), float(longitude), 0.0)


def rasi_chart(jd: float, place: drik.Place) -> list:
    """Raw D1 chart rows: ``[["L", [sign, degree]], [planet_id, [sign, degree]], ...]``."""
    pin_ayanamsa()
    try:
        return charts.rasi_chart(jd, place)
    except Exception as exc:  # PyJHora raises bare exceptions
        raise CalculationError(f"rasi chart failed: {exc}") from exc


def divisional_chart(jd: float, place: drik.Place, factor: int) -> list:
    """Raw divisional chart rows (factor 9 = navamsa)."""
    pin_ayanamsa()
    try:
        return charts.divisional_chart(jd, place, divisional_chart_factor=factor)
    except Exception as exc:  # PyJHora raises bare exceptions
        raise CalculationError(f"divisional chart D{factor} failed: {exc}") from exc


def retrograde_planet_ids(jd: float, place: drik.Place) -> set[int]:
    """Planet ids in retrograde motion at ``jd``.

    Uses ``drik.planets_in_retrograde`` (actual motion) rather than the elongation
    heuristic in ``charts`` — PyJHora's own docstring marks the latter as the fallback.
    """
    pin_ayanamsa()
    try:
        return set(drik.planets_in_retrograde(jd, place))
    except Exception as exc:  # PyJHora raises bare exceptions
        raise CalculationError(f"retrograde detection failed: {exc}") from exc


def split_chart(chart_rows: list) -> tuple[tuple[int, float], list[tuple[int, int, float]]]:
    """Split raw chart rows into ``(ascendant, planets)``.

    Returns ``((sign, degree), [(planet_id, sign, degree), ...])`` with degrees measured
    inside the sign. Rows for outer planets, if PyJHora ever adds them, are ignored — this
    engine speaks only the nine classical bodies.
    """
    ascendant: tuple[int, float] | None = None
    planets: list[tuple[int, int, float]] = []
    for key, (sign, degree) in chart_rows:
        if key == "L":
            ascendant = (int(sign), float(degree))
        elif isinstance(key, int) and key in constants.PLANET_NAMES:
            planets.append((int(key), int(sign), float(degree)))
    if ascendant is None:
        raise CalculationError("chart has no ascendant row")
    return ascendant, planets


def whole_sign_house(planet_sign: int, ascendant_sign: int) -> int:
    """Whole-sign house number 1..12 — the standard Vedic rasi-chart house division."""
    return ((planet_sign - ascendant_sign) % 12) + 1


def sign_name(sign_index: int) -> str:
    return constants.SIGN_NAMES[sign_index % 12]


def nakshatra_name(number: int) -> str:
    """``number`` is 1-based, as PyJHora reports it."""
    return constants.NAKSHATRA_NAMES[(number - 1) % 27]


def clean(value: str) -> str:
    """Strip the zodiac/planet glyphs PyJHora prefixes onto some of its display names."""
    return "".join(ch for ch in value if ch.isascii() and ch.isprintable()).strip()
