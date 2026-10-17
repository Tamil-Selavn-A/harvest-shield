from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health_endpoint_returns_expected_structure():
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


def test_health_endpoint_labels_placeholder_data():
    response = client.get("/api/health/TN001")
    body = response.json()

    assert body["satellite"]["data_status"] == "synthetic"
    assert body["weather"]["data_status"] == "synthetic"

    assert body["satellite"]["ndvi_current"] is None
    assert body["weather"]["temperature_c"] is None
    assert body["weather"]["humidity_pct"] is None
    assert body["weather"]["recent_rainfall_mm"] is None


def test_health_endpoint_returns_404_for_unknown_field():
    response = client.get("/api/health/UNKNOWN")

    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]