from datetime import datetime, timezone
from typing import Any

from backend.schemas.health_schema import (
    CropHealthResponse,
    Recommendation,
    RiskAssessment,
    SatelliteObservation,
    WeatherObservation,
)
from backend.services.field_service import get_field_by_id
from backend.services.weather_service import get_weather_for_field, WeatherDataError


def get_crop_health(field_id: str) -> CropHealthResponse | None:
    """Build an initial crop-health response for a known field.

    Satellite and weather observations are explicitly synthetic placeholders
    until the corresponding team services are integrated.
    """

    field = get_field_by_id(field_id)

    if field is None:
        return None

    satellite = SatelliteObservation(
        field_id=field_id,
        data_source="synthetic_sample",
        data_status="synthetic",
    )

    try:
        weather = get_weather_for_field(field_id)
    except (WeatherDataError, ValueError):
        weather = WeatherObservation(
            field_id=field_id,
            temperature_c=None,
            humidity_pct=None,
            recent_rainfall_mm=None,
            forecast=[],
            data_source="weather_service_error",
            data_status="unavailable",
            observation_time=None,
        )

    risk = RiskAssessment(
        overall_risk="unknown",
        ndvi_risk="unknown",
        weather_risk="unknown",
        disease_risk="unknown",
        explanation=[
            "Satellite observations have not yet been integrated.",
            "Weather observations have not yet been integrated.",
            "Crop risk cannot be assessed reliably without observations.",
        ],
    )

    recommendations = [
        Recommendation(
            action="Collect current satellite and weather observations.",
            priority="medium",
            reason=(
                "Risk assessment is unavailable until the required "
                "observations are integrated."
            ),
            triggers=["satellite_data_unavailable", "weather_data_unavailable"],
        )
    ]

    return CropHealthResponse(
        field=field,
        satellite=satellite,
        weather=weather,
        risk=risk,
        recommendations=recommendations,
        generated_at=datetime.now(timezone.utc),
    )
