from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_list_fields():
    response = client.get("/api/fields")

    assert response.status_code == 200

    body = response.json()

    assert body["count"] == 3
    assert len(body["fields"]) == 3


def test_retrieve_existing_field():
    response = client.get("/api/fields/TN001")

    assert response.status_code == 200

    field = response.json()

    assert field["field_id"] == "TN001"
    assert field["crop_type"] == "rice"


def test_retrieve_another_field():
    response = client.get("/api/fields/TN002")

    assert response.status_code == 200
    assert response.json()["crop_type"] == "millet"


def test_unknown_field_returns_404():
    response = client.get("/api/fields/UNKNOWN")

    assert response.status_code == 404
