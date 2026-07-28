"""Request and response models.

Requests are validated strictly: an out-of-range coordinate or a naive timestamp is a 422,
never a silently wrong chart. Responses are typed loosely (``dict``) on purpose — the
wrappers own their shapes, and re-declaring every nested field here would give two sources
of truth for the same contract.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator

#: PyJHora computes the ascendant with Placidus houses, which are mathematically undefined
#: above the polar circles (~66.56°). Rejecting such latitudes up front turns a guaranteed
#: mid-calculation crash into a clear 422.
POLAR_LATITUDE_LIMIT = 66.5


class BirthPoint(BaseModel):
    """An absolute instant and a place on Earth. The only input this engine understands."""

    utc: datetime = Field(description="Absolute UTC instant, e.g. 1995-06-20T18:30:00Z")
    lat: Annotated[
        float,
        Field(
            ge=-POLAR_LATITUDE_LIMIT,
            le=POLAR_LATITUDE_LIMIT,
            description="Latitude in degrees. Polar-circle latitudes are unsupported "
            "(the house calculation is undefined there).",
        ),
    ]
    lon: Annotated[float, Field(ge=-180, le=180, description="Longitude in degrees")]

    @field_validator("utc")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        """Reject naive timestamps outright.

        A missing offset means the caller has not finished resolving the birthplace's
        timezone. Guessing here would silently shift the ascendant by hours.
        """
        if value.tzinfo is None:
            raise ValueError("utc must include a timezone offset (e.g. trailing 'Z')")
        return value.astimezone(UTC)


class DashaRequest(BirthPoint):
    as_of: datetime | None = Field(
        default=None,
        description="Instant to report the running period for. Defaults to now (UTC).",
    )

    @field_validator("as_of")
    @classmethod
    def _as_of_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("as_of must include a timezone offset")
        return value.astimezone(UTC)


class PanchangaRequest(BirthPoint):
    target_date: date | None = Field(
        default=None,
        description="Evaluate at 00:00 UTC of this date instead of the 'utc' instant.",
    )


class CompatRequest(BaseModel):
    a: BirthPoint
    b: BirthPoint


class EngineResponse(BaseModel):
    """Every response carries these two fields.

    They are what makes a cached result re-identifiable: a caller that stored a chart can
    tell whether it was produced by the parameters currently in force.
    """

    engine_version: str
    ayanamsa: str


class ChartResponse(EngineResponse):
    ascendant: dict[str, Any]
    planets: list[dict[str, Any]]
    navamsa: dict[str, Any]


class DashaResponse(EngineResponse):
    system: str
    cycle_years: int
    as_of: str
    periods: list[dict[str, Any]]
    current: dict[str, Any]


class YogaResponse(EngineResponse):
    yogas: list[dict[str, Any]]
    detected_count: int
    checked_count: int


class PanchangaResponse(EngineResponse):
    evaluated_at: str
    tithi: dict[str, Any]
    nakshatra: dict[str, Any]
    yoga: dict[str, Any]
    karana: dict[str, Any]
    moon_sign: dict[str, Any]


class StrengthResponse(EngineResponse):
    planets: list[dict[str, Any]]


class CompatResponse(EngineResponse):
    porutham_36: float
    max_porutham: int
    score_100: float
    details: list[dict[str, Any]]
    supplementary: dict[str, bool]
    a: dict[str, Any]
    b: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    engine_version: str
    ayanamsa: str
    dasha_system: str
    zodiac: str
    time_basis: str
