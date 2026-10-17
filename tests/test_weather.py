import json
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from backend.schemas.health_schema import WeatherObservation
from backend.services import health_service, weather_service
from backend.services.health_service import get_crop_health
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


def test_incomplete_hourly_rainfall_window_remains_none(monkeypatch):
    payload = _provider_payload()
    payload["hourly"]["time"] = payload["hourly"]["time"][:-1]
    _mock_provider_response(monkeypatch, payload)

    weather = get_weather_for_field("TN001")

    assert weather.recent_rainfall_mm is None
    assert weather.data_status == "live"


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


def test_malformed_provider_shape_uses_synthetic_sample_fallback(monkeypatch):
    _mock_provider_response(monkeypatch, {"current": "not-an-object"})

    weather = get_weather_for_field("TN001")

    assert weather.data_source == "synthetic_sample"
    assert weather.data_status == "synthetic"
    assert weather.temperature_c == 29.4


def test_invalid_field_coordinates_skip_provider_and_use_sample(monkeypatch):
    monkeypatch.setattr(
        weather_service,
        "get_field_by_id",
        lambda field_id: {
            "field_id": field_id,
            "latitude": 91.0,
            "longitude": 76.9558,
        },
    )

    def unexpected_request(request, timeout):
        raise AssertionError("Invalid coordinates must not trigger a provider request")

    monkeypatch.setattr(weather_service, "urlopen", unexpected_request)

    weather = get_weather_for_field("TN001")

    assert weather.temperature_c == 29.4
    assert weather.data_source == "synthetic_sample"
    assert weather.data_status == "synthetic"


def test_offline_fallback_uses_sample_values_not_live_values(monkeypatch):
    _mock_provider_error(monkeypatch, URLError("network unavailable"))

    weather = get_weather_for_field("TN001")

    assert weather.temperature_c == 29.4
    assert weather.humidity_pct == 71.0
    assert weather.recent_rainfall_mm == 2.5
    assert weather.data_source == "synthetic_sample"
    assert weather.data_status == "synthetic"


def test_cached_fallback_returns_shared_weather_observation(monkeypatch):
    _mock_provider_error(monkeypatch, URLError("offline"))
    monkeypatch.setattr(
        weather_service,
        "load_weather_dataset",
        lambda: {
            "metadata": {"latitude": "11.0168", "longitude": "76.9558"},
            "current_weather": {
                "time": "2026-10-17T16:30",
                "temperature_2m (°C)": "27.6",
                "relative_humidity_2m (%)": "73",
                "rain (mm)": "2.5",
            },
            "hourly_weather": [],
            "daily_weather": [],
            "data_source": "Open-Meteo CSV",
            "data_status": "cached",
        },
    )

    weather = get_weather_for_field("TN001")

    assert isinstance(weather, WeatherObservation)
    assert weather.field_id == "TN001"
    assert weather.temperature_c == 27.6
    assert weather.humidity_pct == 73.0
    assert weather.recent_rainfall_mm == 2.5
    assert weather.data_source == "Open-Meteo CSV"
    assert weather.data_status == "cached"


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

def test_health_response_preserves_weather_provenance_and_missing_values(monkeypatch):
    for status, source in (
        ("live", "open-meteo"),
        ("cached", "Open-Meteo CSV"),
        ("synthetic", "synthetic_sample"),
        ("unavailable", "provider_unavailable"),
    ):
        monkeypatch.setattr(
            health_service,
            "get_weather_for_field",
            lambda field_id, status=status, source=source: WeatherObservation(
                field_id=field_id,
                temperature_c=None,
                humidity_pct=None,
                recent_rainfall_mm=None,
                forecast=[],
                data_source=source,
                data_status=status,
                observation_time=None,
            ),
        )

        result = get_crop_health("TN001")

        assert result is not None
        assert result.weather.data_source == source
        assert result.weather.data_status == status
        assert result.weather.temperature_c is None
        assert result.weather.humidity_pct is None
        assert result.weather.recent_rainfall_mm is None
        assert result.weather.forecast == []
        assert result.weather.observation_time is None
        assert result.risk.overall_risk == "unknown"
        assert result.risk.weather_risk == "unknown"

def test_nonmatching_cached_coordinates_fall_through_to_synthetic(monkeypatch):
    _mock_provider_error(monkeypatch, URLError("offline"))
    monkeypatch.setattr(
        weather_service,
        "load_weather_dataset",
        lambda: {
            "metadata": {"latitude": "12.6889", "longitude": "77.1195"},
            "current_weather": {
                "time": "2026-10-17T16:30",
                "temperature_2m (°C)": "19.0",
                "relative_humidity_2m (%)": "80",
                "rain (mm)": "4.0",
            },
            "hourly_weather": [],
            "daily_weather": [],
            "data_source": "Open-Meteo CSV",
            "data_status": "cached",
        },
    )

    weather = get_weather_for_field("TN001")

    assert isinstance(weather, WeatherObservation)
    assert weather.data_status == "synthetic"
    assert weather.data_source == "synthetic_sample"
    assert weather.temperature_c == 29.4


def test_missing_synthetic_record_returns_unavailable_after_cache_mismatch(
    tmp_path, monkeypatch
):
    sample_path = tmp_path / "weather_sample.json"
    sample_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(weather_service, "_SAMPLE_PATH", sample_path)
    monkeypatch.setattr(
        weather_service,
        "load_weather_dataset",
        lambda: {
            "metadata": {"latitude": "12.6889", "longitude": "77.1195"},
            "current_weather": {"time": "2026-10-17T16:30"},
            "data_source": "Open-Meteo CSV",
            "data_status": "cached",
        },
    )
    _mock_provider_error(monkeypatch, URLError("offline"))

    weather = get_weather_for_field("TN001")

    assert isinstance(weather, WeatherObservation)
    assert weather.field_id == "TN001"
    assert weather.data_status == "unavailable"
    assert weather.data_source == "synthetic_sample_missing"
    assert weather.temperature_c is None
    assert weather.humidity_pct is None
    assert weather.recent_rainfall_mm is None
    assert weather.forecast == []
    assert weather.observation_time is None
