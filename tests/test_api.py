"""HTTP contract — the surface the calling backend actually depends on."""

from __future__ import annotations

from conftest import AS_OF, BIRTHS_BY_KEY, Birth
from fastapi.testclient import TestClient

import constants

_SEOUL = BIRTHS_BY_KEY["seoul_1990"]
_BUSAN = BIRTHS_BY_KEY["busan_1978"]

_SIMPLE_ENDPOINTS = ("/v1/chart", "/v1/yoga", "/v1/panchanga", "/v1/strength")


def test_health_reports_fixed_parameters(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["ayanamsa"] == constants.AYANAMSA
    assert body["dasha_system"] == constants.DASHA_SYSTEM
    assert body["zodiac"] == "sidereal"
    assert body["time_basis"] == "utc"


def test_every_response_is_reidentifiable(client: TestClient, birth: Birth) -> None:
    """engine_version + ayanamsa on every payload — this is what makes caches invalidatable."""
    for path in _SIMPLE_ENDPOINTS:
        body = client.post(path, json=birth.body()).json()
        assert body["engine_version"] == constants.ENGINE_VERSION, path
        assert body["ayanamsa"] == constants.AYANAMSA, path

    dasha = client.post("/v1/dasha", json={**birth.body(), "as_of": AS_OF.isoformat()}).json()
    assert dasha["engine_version"] == constants.ENGINE_VERSION

    compat = client.post("/v1/compat", json={"a": birth.body(), "b": _BUSAN.body()}).json()
    assert compat["engine_version"] == constants.ENGINE_VERSION


def test_chart_shape(client: TestClient) -> None:
    body = client.post("/v1/chart", json=_SEOUL.body()).json()
    assert set(body["ascendant"]) == {"sign", "sign_index", "degree"}
    assert len(body["planets"]) == 9
    assert set(body["planets"][0]) == {
        "id", "name", "sign", "sign_index", "house", "degree", "retrograde"
    }
    assert len(body["navamsa"]["planets"]) == 9


def test_dasha_shape(client: TestClient) -> None:
    body = client.post(
        "/v1/dasha", json={**_SEOUL.body(), "as_of": AS_OF.isoformat()}
    ).json()
    assert body["system"] == "vimshottari"
    assert len(body["periods"]) == 9
    assert body["current"]["lord"] in constants.PLANET_NAMES.values()
    assert body["current"]["start"] < body["current"]["end"]


def test_dasha_as_of_defaults_to_now(client: TestClient) -> None:
    """Omitting as_of must still work — the field is a reproducibility aid, not a requirement."""
    body = client.post("/v1/dasha", json=_SEOUL.body())
    assert body.status_code == 200
    assert body.json()["current"]["lord"] is not None


def test_panchanga_target_date_overrides_instant(client: TestClient) -> None:
    at_birth = client.post("/v1/panchanga", json=_SEOUL.body()).json()
    at_date = client.post(
        "/v1/panchanga", json={**_SEOUL.body(), "target_date": "2026-07-27"}
    ).json()
    assert at_date["evaluated_at"].startswith("2026-07-27")
    assert at_date["tithi"]["number"] != at_birth["tithi"]["number"]


def test_strength_covers_seven_planets_and_ranks_them(client: TestClient) -> None:
    body = client.post("/v1/strength", json=_SEOUL.body()).json()
    assert len(body["planets"]) == 7
    assert sorted(planet["rank"] for planet in body["planets"]) == list(range(1, 8))
    assert all(0 <= planet["score_100"] <= 100 for planet in body["planets"])


def test_yoga_returns_everything_it_detected(client: TestClient) -> None:
    body = client.post("/v1/yoga", json=_SEOUL.body()).json()
    assert body["detected_count"] == len(body["yogas"])
    assert body["checked_count"] >= body["detected_count"]
    assert all(yoga["key"] and yoga["name"] for yoga in body["yogas"])


def test_compat_totals_the_eight_kutas(client: TestClient) -> None:
    body = client.post("/v1/compat", json={"a": _SEOUL.body(), "b": _BUSAN.body()}).json()
    assert body["max_porutham"] == 36
    assert 0 <= body["porutham_36"] <= 36
    assert len(body["details"]) == 8
    assert abs(sum(detail["points"] for detail in body["details"]) - body["porutham_36"]) < 1e-6
    assert body["score_100"] == round(body["porutham_36"] / 36 * 100, 2)


# --- input validation is a 4xx, never a wrong chart ---------------------------


def test_naive_timestamp_is_rejected(client: TestClient) -> None:
    """No offset means the caller has not finished resolving the timezone."""
    response = client.post(
        "/v1/chart", json={"utc": "1990-05-15T14:30:00", "lat": 37.5, "lon": 127.0}
    )
    assert response.status_code == 422


def test_out_of_range_coordinates_are_rejected(client: TestClient) -> None:
    for lat, lon in ((91.0, 0.0), (-91.0, 0.0), (0.0, 181.0), (0.0, -181.0)):
        response = client.post(
            "/v1/chart", json={"utc": "1990-05-15T14:30:00Z", "lat": lat, "lon": lon}
        )
        assert response.status_code == 422, (lat, lon)


def test_unparseable_date_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/v1/chart", json={"utc": "not-a-date", "lat": 37.5, "lon": 127.0}
    )
    assert response.status_code == 422


def test_missing_fields_are_rejected(client: TestClient) -> None:
    assert client.post("/v1/chart", json={"lat": 37.5, "lon": 127.0}).status_code == 422
    assert client.post("/v1/compat", json={"a": _SEOUL.body()}).status_code == 422
