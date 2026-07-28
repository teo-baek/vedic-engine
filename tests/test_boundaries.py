"""Edge cases that break naive implementations — none of these may raise.

Covers the boundary list from the engine's acceptance criteria: midnight either side,
a leap day, a daylight-saving transition instant, high latitude and the southern hemisphere.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

_EDGE_CASES: tuple[tuple[str, datetime, float, float], ...] = (
    ("just_before_midnight", datetime(1999, 12, 31, 23, 59, 59, tzinfo=UTC), 37.5665, 126.9780),
    ("exact_midnight", datetime(2000, 1, 1, 0, 0, 0, tzinfo=UTC), 37.5665, 126.9780),
    ("just_after_midnight", datetime(2000, 1, 1, 0, 0, 1, tzinfo=UTC), 37.5665, 126.9780),
    ("leap_day", datetime(2000, 2, 29, 12, 0, tzinfo=UTC), 48.8566, 2.3522),
    ("leap_day_1996", datetime(1996, 2, 29, 3, 20, tzinfo=UTC), 40.7128, -74.0060),
    # The instant US clocks sprang forward in 1995 — meaningless locally, ordinary in UTC.
    ("dst_spring_forward", datetime(1995, 4, 2, 7, 0, tzinfo=UTC), 40.7128, -74.0060),
    ("dst_fall_back", datetime(1995, 10, 29, 6, 0, tzinfo=UTC), 40.7128, -74.0060),
    # Korea's own daylight-saving experiment; the engine sees only the resolved instant.
    ("korea_dst_1988", datetime(1988, 8, 15, 0, 0, tzinfo=UTC), 37.5665, 126.9780),
    # Highest latitudes inside the supported band (see POLAR_LATITUDE_LIMIT).
    ("high_latitude_north", datetime(1980, 6, 21, 12, 0, tzinfo=UTC), 64.1466, -21.9426),
    ("high_latitude_south", datetime(1980, 12, 21, 12, 0, tzinfo=UTC), -54.8019, -68.3030),
    ("southern_hemisphere", datetime(2001, 12, 10, 22, 45, tzinfo=UTC), -33.8688, 151.2093),
    ("equator", datetime(1975, 3, 21, 6, 0, tzinfo=UTC), 0.0, 0.0),
    ("date_line_east", datetime(1985, 7, 4, 11, 11, tzinfo=UTC), -18.1416, 178.4419),
    ("earliest_supported", datetime(1900, 1, 1, 12, 0, tzinfo=UTC), 51.5074, -0.1278),
    ("far_future", datetime(2099, 12, 31, 12, 0, tzinfo=UTC), 35.6762, 139.6503),
)

_IDS = [case[0] for case in _EDGE_CASES]


@pytest.mark.parametrize(("name", "moment", "lat", "lon"), _EDGE_CASES, ids=_IDS)
def test_chart_survives_edge_cases(
    client: TestClient, name: str, moment: datetime, lat: float, lon: float
) -> None:
    response = client.post(
        "/v1/chart", json={"utc": moment.isoformat(), "lat": lat, "lon": lon}
    )
    assert response.status_code == 200, f"{name}: {response.text[:200]}"
    body = response.json()
    assert len(body["planets"]) == 9
    assert 0 <= body["ascendant"]["sign_index"] <= 11
    assert 0.0 <= body["ascendant"]["degree"] < 30.0


@pytest.mark.parametrize(("name", "moment", "lat", "lon"), _EDGE_CASES, ids=_IDS)
def test_panchanga_survives_edge_cases(
    client: TestClient, name: str, moment: datetime, lat: float, lon: float
) -> None:
    response = client.post(
        "/v1/panchanga", json={"utc": moment.isoformat(), "lat": lat, "lon": lon}
    )
    assert response.status_code == 200, f"{name}: {response.text[:200]}"
    body = response.json()
    assert 1 <= body["nakshatra"]["number"] <= 27
    assert 1 <= body["nakshatra"]["pada"] <= 4
    assert 0 <= body["moon_sign"]["sign_index"] <= 11


@pytest.mark.parametrize(("name", "moment", "lat", "lon"), _EDGE_CASES, ids=_IDS)
def test_dasha_survives_edge_cases(
    client: TestClient, name: str, moment: datetime, lat: float, lon: float
) -> None:
    response = client.post(
        "/v1/dasha",
        json={"utc": moment.isoformat(), "lat": lat, "lon": lon, "as_of": "2026-07-27T00:00:00Z"},
    )
    assert response.status_code == 200, f"{name}: {response.text[:200]}"
    assert len(response.json()["periods"]) == 9


def test_as_of_outside_the_life_window_is_a_null_current_not_an_error(
    client: TestClient,
) -> None:
    """A 1900 birth has finished its 120-year cycle by 2026; a 2099 birth has not begun.

    Both are legitimate queries — the timeline itself is still returned; only ``current``
    has nothing to point at.
    """
    for utc in ("1900-01-01T12:00:00Z", "2099-12-31T12:00:00Z"):
        response = client.post(
            "/v1/dasha",
            json={"utc": utc, "lat": 51.5, "lon": 0.0, "as_of": "2026-07-27T00:00:00Z"},
        )
        assert response.status_code == 200, response.text[:200]
        body = response.json()
        assert len(body["periods"]) == 9
        assert body["current"]["lord"] is None
        assert body["current"]["sub_lord"] is None


def test_polar_latitudes_are_rejected_up_front(client: TestClient) -> None:
    """Poles and polar-circle latitudes: house math is undefined, so the schema says no."""
    for lat in (90.0, -90.0, 69.6496, -77.85):
        response = client.post(
            "/v1/chart", json={"utc": "1990-05-15T14:30:00Z", "lat": lat, "lon": 0.0}
        )
        assert response.status_code == 422, f"lat={lat} -> {response.status_code}"
