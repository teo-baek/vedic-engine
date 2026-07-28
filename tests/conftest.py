"""Shared fixtures and the five reference births used across the suite.

The births span the cases that break naive implementations: a Korean birth during the
1987-88 daylight-saving experiment is *not* included on purpose — timezone handling is the
caller's job and this engine only ever sees UTC.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

import pytest
from fastapi.testclient import TestClient

import main

GOLDEN_DIR = Path(__file__).parent / "golden"


class Birth(NamedTuple):
    key: str
    utc: datetime
    lat: float
    lon: float
    note: str

    def body(self) -> dict[str, Any]:
        return {"utc": self.utc.isoformat(), "lat": self.lat, "lon": self.lon}


#: Korea 2 / United States 1 / Europe 1 / southern hemisphere 1.
BIRTHS: tuple[Birth, ...] = (
    Birth("seoul_1990", datetime(1990, 5, 15, 14, 30, tzinfo=UTC), 37.5665, 126.9780,
          "Seoul, 1990-05-15 23:30 KST"),
    Birth("busan_1978", datetime(1978, 11, 2, 21, 15, tzinfo=UTC), 35.1796, 129.0756,
          "Busan, 1978-11-03 06:15 KST"),
    Birth("newyork_1995", datetime(1995, 6, 20, 18, 30, tzinfo=UTC), 40.7128, -74.0060,
          "New York, 1995-06-20 14:30 EDT"),
    Birth("london_1963", datetime(1963, 2, 28, 3, 5, tzinfo=UTC), 51.5074, -0.1278,
          "London, 1963-02-28 03:05 GMT"),
    Birth("sydney_2001", datetime(2001, 12, 10, 22, 45, tzinfo=UTC), -33.8688, 151.2093,
          "Sydney, 2001-12-11 09:45 AEDT"),
)

BIRTHS_BY_KEY = {birth.key: birth for birth in BIRTHS}

#: Fixed reference instant so dasha output is reproducible.
AS_OF = datetime(2026, 7, 27, 0, 0, tzinfo=UTC)


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(main.app)


def load_golden(name: str) -> dict[str, Any]:
    return json.loads((GOLDEN_DIR / f"{name}.json").read_text(encoding="utf-8"))


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrise any test taking a ``birth`` argument over all five reference births."""
    if "birth" in metafunc.fixturenames:
        metafunc.parametrize("birth", BIRTHS, ids=[b.key for b in BIRTHS])
