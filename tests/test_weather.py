import json
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from backend.services import weather_service
from backend.services.weather_service import get_weather_for_field


class FakeResponse:
    def __init__(self, payload):
        if isinstance(payload, bytes):
            self.body = payload
        else:
            self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body


def _provider_payload():
    current_time = datetime(2026, 10, 17, 16, 30)
    last_hour = current_time.replace(minute=0)
    hourly_times = [
        (last_hour - timedelta(hours=hours_ago)).isoformat(timespec="minutes")
        for hours_ago in range(24, 0, -1)
    ]
    return {
        "utc_offset_seconds": 19800,
        "current": {
            "time": current_time.isoformat(timespec="minutes"),
            "temperature_2m": 27.6,
            "relative_humidity_2m": 73,
        },
        "hourly": {
            "time": hourly_times,
            "precipitation": [0.5] * 24,
        },
        "daily": {
            "time": ["2026-10-17", "2026-10-18", "2026-10-19"],
            "temperature_2m_max": [30.4, 29.2, 28.8],
            "precipitation_sum": [2.9, 8.6, 1.2],
        },
    }


def _mock_provider_response(monkeypatch, payload):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(payload)

    monkeypatch.setattr(weather_service, "urlopen", fake_urlopen)
    return captured


def _mock_provider_error(monkeypatch, error):
    def fake_urlopen(request, timeout):
        raise error

    monkeypatch.setattr(weather_service, "urlopen", fake_urlopen)


def test_valid_provider_response_maps_values_and_provenance(monkeypatch):
    captured = _mock_provider_response(monkeypatch, _provider_payload())

    weather = get_weather_for_field("TN001")

    assert weather.field_id == "TN001"
    assert weather.temperature_c == 27.6
    assert weather.humidity_pct == 73.0
    assert weather.recent_rainfall_mm == 12.0
    assert weather.forecast == [
        {
            "date": "2026-10-18",
            "temperature_c": 29.2,
            "precipitation_mm": 8.6,
        },
        {
            "date": "2026-10-19",
            "temperature_c": 28.8,
            "precipitation_mm": 1.2,
        },
    ]
    assert weather.data_source == "open-meteo"
    assert weather.data_status == "live"
    assert weather.observation_time.isoformat() == "2026-10-17T16:30:00+05:30"
    assert captured["timeout"] == weather_service._TIMEOUT_SECONDS

    query = parse_qs(urlsplit(captured["request"].full_url).query)
    assert query["latitude"] == ["11.0168"]
    assert query["longitude"] == ["76.9558"]


def test_missing_provider_values_remain_none(monkeypatch):
    payload = _provider_payload()
    payload["current"]["temperature_2m"] = None
    payload["current"].pop("relative_humidity_2m")
    payload["hourly"]["precipitation"][-1] = None
    payload["daily"]["temperature_2m_max"][1] = None
    payload["daily"]["precipitation_sum"][1] = -0.1
    _mock_provider_response(monkeypatch, payload)

    weather = get_weather_for_field("TN001")

    assert weather.temperature_c is None
    assert weather.humidity_pct is None
    assert weather.recent_rainfall_mm is None
    assert weather.forecast[0]["temperature_c"] is None
    assert weather.forecast[0]["precipitation_mm"] is None


def test_connection_timeout_uses_synthetic_sample_fallback(monkeypatch):
    _mock_provider_error(monkeypatch, TimeoutError("request timed out"))

    weather = get_weather_for_field("TN001")

    assert weather.temperature_c == 29.4
    assert weather.data_source == "synthetic_sample"
    assert weather.data_status == "synthetic"


def test_provider_http_error_uses_synthetic_sample_fallback(monkeypatch):
    error = HTTPError(
        "https://api.open-meteo.com/v1/forecast",
        503,
        "service unavailable",
        None,
        None,
    )
    _mock_provider_error(monkeypatch, error)

    weather = get_weather_for_field("TN001")

    assert weather.data_source == "synthetic_sample"
    assert weather.data_status == "synthetic"
    assert weather.temperature_c == 29.4


def test_malformed_provider_json_uses_synthetic_sample_fallback(monkeypatch):
    _mock_provider_response(monkeypatch, b"{not-json")

    weather = get_weather_for_field("TN001")

    assert weather.data_source == "synthetic_sample"
    assert weather.data_status == "synthetic"
    assert weather.temperature_c == 29.4


def test_offline_fallback_uses_sample_values_not_live_values(monkeypatch):
    _mock_provider_error(monkeypatch, URLError("network unavailable"))

    weather = get_weather_for_field("TN001")

    assert weather.temperature_c == 29.4
    assert weather.humidity_pct == 71.0
    assert weather.recent_rainfall_mm == 2.5
    assert weather.data_source == "synthetic_sample"
    assert weather.data_status == "synthetic"


def test_missing_sample_variables_remain_none(tmp_path, monkeypatch):
    sample_path = tmp_path / "weather_sample.json"
    sample_path.write_text(
        json.dumps(
            {
                "TN001": {
                    "field_id": "TN001",
                    "data_source": "synthetic_sample",
                    "data_status": "synthetic",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(weather_service, "_SAMPLE_PATH", sample_path)
    _mock_provider_error(monkeypatch, URLError("offline"))

    weather = get_weather_for_field("TN001")

    assert weather.temperature_c is None
    assert weather.humidity_pct is None
    assert weather.recent_rainfall_mm is None
    assert weather.forecast == []


def test_unknown_field_returns_unavailable_without_provider_request(monkeypatch):
    def unexpected_request(request, timeout):
        raise AssertionError("Unknown fields must not trigger a provider request")

    monkeypatch.setattr(weather_service, "urlopen", unexpected_request)

    weather = get_weather_for_field("UNKNOWN")

    assert weather.field_id == "UNKNOWN"
    assert weather.temperature_c is None
    assert weather.humidity_pct is None
    assert weather.recent_rainfall_mm is None
    assert weather.forecast == []
    assert weather.data_source == "field_not_found"
    assert weather.data_status == "unavailable"
    assert weather.observation_time is None
