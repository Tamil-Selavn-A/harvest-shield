"""Weather service using Open-Meteo with a clearly labelled offline fallback."""

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.schemas.health_schema import WeatherObservation
from backend.services.field_service import get_field_by_id


_SAMPLE_PATH = Path(__file__).resolve().parents[2] / "data" / "weather_sample.json"
_API_URL = "https://api.open-meteo.com/v1/forecast"
_TIMEOUT_SECONDS = 5


def _unavailable_weather(field_id: str, data_source: str) -> WeatherObservation:
    """Build a response that makes missing weather data explicit."""
    return WeatherObservation(
        field_id=field_id,
        temperature_c=None,
        humidity_pct=None,
        recent_rainfall_mm=None,
        forecast=[],
        data_source=data_source,
        data_status="unavailable",
        observation_time=None,
    )


def _optional_number(value: Any) -> float | None:
    """Return finite numeric data as a float; preserve invalid or missing values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    return float(value)


def _read_sample_weather(field_id: str) -> WeatherObservation:
    """Load the labelled synthetic sample for a known field."""
    try:
        sample_data: Any = json.loads(_SAMPLE_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return _unavailable_weather(field_id, "synthetic_sample_unavailable")

    if not isinstance(sample_data, dict):
        return _unavailable_weather(field_id, "synthetic_sample_invalid")

    record = sample_data.get(field_id)
    if not isinstance(record, dict):
        return _unavailable_weather(field_id, "synthetic_sample_missing")

    try:
        return WeatherObservation(**record)
    except (TypeError, ValueError):
        return _unavailable_weather(field_id, "synthetic_sample_invalid")


def _observation_datetime(current: dict[str, Any], payload: dict[str, Any]) -> datetime:
    """Parse Open-Meteo's local timestamp and attach its returned UTC offset."""
    raw_time = current.get("time")
    if not isinstance(raw_time, str):
        raise ValueError("Open-Meteo response is missing current.time")

    observed_at = datetime.fromisoformat(raw_time)
    if observed_at.tzinfo is not None:
        return observed_at

    offset_seconds = payload.get("utc_offset_seconds")
    if isinstance(offset_seconds, bool) or not isinstance(offset_seconds, int):
        raise ValueError("Open-Meteo response is missing a valid UTC offset")

    return observed_at.replace(
        tzinfo=timezone(timedelta(seconds=offset_seconds))
    )


def _recent_rainfall_mm(
    hourly: Any,
    current_time: str,
) -> float | None:
    """Sum the preceding 24 hourly precipitation values when all are available."""
    if not isinstance(hourly, dict):
        return None

    times = hourly.get("time")
    precipitation = hourly.get("precipitation")
    if not isinstance(times, list) or not isinstance(precipitation, list):
        return None
    if len(times) != len(precipitation):
        return None

    past_values = [
        value
        for time_value, value in zip(times, precipitation)
        if isinstance(time_value, str) and time_value < current_time
    ][-24:]

    if len(past_values) != 24:
        return None

    numbers = [_optional_number(value) for value in past_values]
    if any(value is None or value < 0 for value in numbers):
        return None

    return sum(numbers)


def _forecast_entries(daily: Any, observation_time: datetime) -> list[dict[str, Any]]:
    """Normalize future daily maximum temperature and precipitation."""
    if not isinstance(daily, dict):
        return []

    dates = daily.get("time")
    temperatures = daily.get("temperature_2m_max")
    precipitation = daily.get("precipitation_sum")
    if not all(isinstance(values, list) for values in (dates, temperatures, precipitation)):
        return []
    if not (len(dates) == len(temperatures) == len(precipitation)):
        return []

    today = observation_time.date().isoformat()
    forecast = []
    for date_value, temperature, rain in zip(dates, temperatures, precipitation):
        if not isinstance(date_value, str) or date_value <= today:
            continue
        precipitation_mm = _optional_number(rain)
        if precipitation_mm is not None and precipitation_mm < 0:
            precipitation_mm = None
        forecast.append(
            {
                "date": date_value,
                "temperature_c": _optional_number(temperature),
                "precipitation_mm": precipitation_mm,
            }
        )
    return forecast


def _fetch_live_weather(field: dict[str, Any]) -> WeatherObservation:
    """Request and normalize one field's current weather and forecast."""
    latitude = _optional_number(field.get("latitude"))
    longitude = _optional_number(field.get("longitude"))
    if latitude is None or not -90 <= latitude <= 90:
        raise ValueError("Field latitude is invalid")
    if longitude is None or not -180 <= longitude <= 180:
        raise ValueError("Field longitude is invalid")

    parameters = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m",
            "hourly": "precipitation",
            "daily": "temperature_2m_max,precipitation_sum",
            "past_hours": 24,
            "forecast_hours": 48,
            "forecast_days": 3,
            "timezone": "auto",
        }
    )
    request = Request(
        f"{_API_URL}?{parameters}",
        headers={"Accept": "application/json"},
    )

    with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
        payload: Any = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("Open-Meteo response must be a JSON object")

    current = payload.get("current")
    if not isinstance(current, dict):
        raise ValueError("Open-Meteo response is missing current weather")

    observed_at = _observation_datetime(current, payload)
    current_time = current.get("time")
    if not isinstance(current_time, str):
        raise ValueError("Open-Meteo response is missing current.time")

    temperature = _optional_number(current.get("temperature_2m"))
    humidity = _optional_number(current.get("relative_humidity_2m"))
    if humidity is not None and not 0 <= humidity <= 100:
        humidity = None

    return WeatherObservation(
        field_id=field["field_id"],
        temperature_c=temperature,
        humidity_pct=humidity,
        recent_rainfall_mm=_recent_rainfall_mm(
            payload.get("hourly"),
            current_time,
        ),
        forecast=_forecast_entries(payload.get("daily"), observed_at),
        data_source="open-meteo",
        data_status="live",
        observation_time=observed_at,
    )


def get_weather_for_field(field_id: str) -> WeatherObservation:
    """Return live weather when available, otherwise labelled sample data."""
    field = get_field_by_id(field_id)
    if field is None:
        return _unavailable_weather(field_id, "field_not_found")

    try:
        return _fetch_live_weather(field)
    except (URLError, TimeoutError, OSError, ValueError, TypeError, KeyError):
        return _read_sample_weather(field_id)
