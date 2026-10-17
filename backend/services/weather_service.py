import csv
from pathlib import Path
from typing import Any

from backend.services.field_service import get_field_by_id


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEATHER_FILE = PROJECT_ROOT / "data" / "open_meteo_weather.csv"


class WeatherDataError(Exception):
    """Raised when the weather dataset cannot be read or parsed."""


def load_weather_dataset() -> dict[str, Any]:
    """Read the metadata, current, hourly, and daily CSV sections."""

    try:
        lines = WEATHER_FILE.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise WeatherDataError(f"Cannot read weather file: {WEATHER_FILE}") from exc

    metadata = None
    current_header = None
    hourly_header = None
    daily_header = None

    for index, line in enumerate(lines):
        if line.startswith("latitude,longitude,elevation,"):
            rows = list(csv.DictReader(lines[index:index + 2]))
            metadata = rows[0] if rows else None
        elif (
            line.startswith("time,temperature_2m")
            and "relative_humidity_2m" in line
            and "wind_speed_10m" in line
        ):
            current_header = index
        elif (
            line.startswith("time,temperature_2m")
            and "relative_humidity_2m" in line
            and "wind_speed_10m" not in line
        ):
            hourly_header = index
        elif line.startswith("time,weather_code"):
            daily_header = index

    if None in (metadata, current_header, hourly_header, daily_header):
        raise WeatherDataError("One or more expected CSV sections are missing.")

    current_rows = list(csv.DictReader(lines[current_header:current_header + 2]))
    hourly_rows = list(csv.DictReader(line for line in lines[hourly_header:daily_header] if line.strip()))
    daily_rows = list(csv.DictReader(line for line in lines[daily_header:] if line.strip()))

    return {
        "metadata": metadata,
        "current_weather": current_rows[0] if current_rows else None,
        "hourly_weather": hourly_rows,
        "daily_weather": daily_rows,
        "data_source": "Open-Meteo CSV",
        "data_status": "cached",
    }


def get_weather_for_field(field_id: str) -> dict[str, Any]:
    """Return weather only if the CSV coordinates match the selected field."""

    field = get_field_by_id(field_id)
    if field is None:
        raise ValueError(f"Unknown field ID: {field_id}")

    dataset = load_weather_dataset()
    metadata = dataset["metadata"]
    latitude = float(metadata["latitude"])
    longitude = float(metadata["longitude"])

    matches = (
        abs(float(field["latitude"]) - latitude) < 0.01
        and abs(float(field["longitude"]) - longitude) < 0.01
    )

    if not matches:
        return {
            "field_id": field_id,
            "temperature_c": None,
            "humidity_pct": None,
            "recent_rainfall_mm": None,
            "forecast": [],
            "data_source": "Open-Meteo CSV",
            "data_status": "unavailable",
            "observation_time": None,
            "message": "Weather coordinates do not match this field.",
            "weather_coordinates": {
                "latitude": latitude,
                "longitude": longitude,
            },
        }

    current = dataset["current_weather"]
    if not current:
        raise WeatherDataError("The CSV contains no current weather row.")

    return {
        "field_id": field_id,
        "temperature_c": float(current["temperature_2m (°C)"]),
        "humidity_pct": float(current["relative_humidity_2m (%)"]),
        "recent_rainfall_mm": float(current["rain (mm)"]),
        "forecast": [],
        "data_source": dataset["data_source"],
        "data_status": dataset["data_status"],
        "observation_time": current["time"],
        "weather_coordinates": {
            "latitude": latitude,
            "longitude": longitude,
        },
    }


