from fastapi.testclient import TestClient

from backend.schemas.health_schema import WeatherObservation
from backend.services import health_service

from backend.main import app


client = TestClient(app)


def test_health_endpoint_returns_expected_structure(monkeypatch):
    monkeypatch.setattr(
        health_service,
        "get_weather_for_field",
        lambda field_id: WeatherObservation(
            field_id=field_id,
            temperature_c=27.6,
            humidity_pct=73.0,
            recent_rainfall_mm=2.5,
            forecast=[],
            data_source="open-meteo-test-fixture",
            data_status="live",
        ),
    )
    response = client.get("/api/health/TN001")

    assert response.status_code == 200

    body = response.json()

    assert body["field"]["field_id"] == "TN001"
    assert body["satellite"]["field_id"] == "TN001"
    assert body["weather"]["field_id"] == "TN001"

    assert body["risk"]["overall_risk"] == "unknown"
    assert isinstance(body["recommendations"], list)
    assert body["generated_at"]
    assert body["disclaimer"]


def test_health_endpoint_labels_placeholder_data(monkeypatch):
    monkeypatch.setattr(
        health_service,
        "get_weather_for_field",
        lambda field_id: WeatherObservation(
            field_id=field_id,
            temperature_c=None,
            humidity_pct=None,
            recent_rainfall_mm=None,
            forecast=[],
            data_source="test_unavailable_fixture",
            data_status="unavailable",
            observation_time=None,
        ),
    )
    response = client.get("/api/health/TN001")
    body = response.json()

    assert body["satellite"]["data_status"] == "synthetic"
    assert body["weather"]["data_status"] == "unavailable"
    assert body["weather"]["temperature_c"] is None
    assert body["weather"]["humidity_pct"] is None
    assert body["weather"]["recent_rainfall_mm"] is None
    assert body["weather"]["data_source"] == "test_unavailable_fixture"

    assert body["satellite"]["ndvi_current"] is None
    assert body["weather"]["temperature_c"] is None
    assert body["weather"]["humidity_pct"] is None
    assert body["weather"]["recent_rainfall_mm"] is None


def test_health_endpoint_returns_404_for_unknown_field():
    response = client.get("/api/health/UNKNOWN")

    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]
