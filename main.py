"""Stateless Vedic astronomy calculation API.

Six endpoints, one input shape, no storage. Every response echoes ``engine_version`` and
``ayanamsa`` so a caller can tell which parameters produced a cached result.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException

import constants
import schemas
from wrappers import _engine, chart, compat, dasha, panchanga, strength, yoga

log = logging.getLogger("vedic_engine")

app = FastAPI(
    title="vedic-engine",
    version=constants.ENGINE_VERSION,
    description=(
        "Stateless sidereal (Lahiri) astronomy calculations built on PyJHora. "
        "Accepts UTC instants and coordinates only — it holds no timezone data and no state."
    ),
)


def _stamp(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach the reproducibility fields carried by every response."""
    return {
        "engine_version": constants.ENGINE_VERSION,
        "ayanamsa": constants.AYANAMSA,
        **payload,
    }


def _guard(operation: str, func: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
    """Run a wrapper, converting calculation failures into a 500 with no internals leaked.

    Input problems are already 422s from pydantic. Anything reaching here is the engine's
    own fault, so the caller gets a generic message and the detail goes to the log.
    """
    try:
        return _stamp(func(*args, **kwargs))
    except _engine.CalculationError:
        log.exception("%s: calculation failed", operation)
        raise HTTPException(status_code=500, detail="calculation failed") from None
    except Exception:  # PyJHora raises bare exceptions from deep inside
        log.exception("%s: unexpected failure", operation)
        raise HTTPException(status_code=500, detail="calculation failed") from None


@app.get("/health", response_model=schemas.HealthResponse)
def health() -> dict[str, Any]:
    """Liveness plus the fixed parameters in force. Cheap enough for Cloud Run probes."""
    return {
        "status": "ok",
        "engine_version": constants.ENGINE_VERSION,
        "ayanamsa": constants.AYANAMSA,
        "dasha_system": constants.DASHA_SYSTEM,
        "zodiac": constants.ZODIAC,
        "time_basis": constants.TIME_BASIS,
    }


@app.post("/v1/chart", response_model=schemas.ChartResponse)
def post_chart(body: schemas.BirthPoint) -> dict[str, Any]:
    """Rasi (D1) and navamsa (D9) positions."""
    return _guard("chart", chart.compute, body.utc, body.lat, body.lon)


@app.post("/v1/dasha", response_model=schemas.DashaResponse)
def post_dasha(body: schemas.DashaRequest) -> dict[str, Any]:
    """Vimshottari 120-year timeline and the currently running period."""
    return _guard("dasha", dasha.compute, body.utc, body.lat, body.lon, body.as_of)


@app.post("/v1/yoga", response_model=schemas.YogaResponse)
def post_yoga(body: schemas.BirthPoint) -> dict[str, Any]:
    """Every detected yoga. Selection is the caller's job."""
    return _guard("yoga", yoga.compute, body.utc, body.lat, body.lon)


@app.post("/v1/panchanga", response_model=schemas.PanchangaResponse)
def post_panchanga(body: schemas.PanchangaRequest) -> dict[str, Any]:
    """Tithi, nakshatra, yoga, karana and Moon sign."""
    return _guard(
        "panchanga", panchanga.compute, body.utc, body.lat, body.lon, body.target_date
    )


@app.post("/v1/strength", response_model=schemas.StrengthResponse)
def post_strength(body: schemas.BirthPoint) -> dict[str, Any]:
    """Shadbala for the seven classical planets, normalised to 0-100."""
    return _guard("strength", strength.compute, body.utc, body.lat, body.lon)


@app.post("/v1/compat", response_model=schemas.CompatResponse)
def post_compat(body: schemas.CompatRequest) -> dict[str, Any]:
    """Ashtakoota matching between two birth points."""
    return _guard(
        "compat",
        compat.compute,
        body.a.utc,
        body.a.lat,
        body.a.lon,
        body.b.utc,
        body.b.lat,
        body.b.lon,
    )
