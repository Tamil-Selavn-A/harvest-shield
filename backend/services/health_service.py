from datetime import datetime, timezone

from backend.schemas.health_schema import (
    CropHealthResponse,
    RiskAssessment,
    SatelliteObservation,
    WeatherObservation,
)
from backend.services.field_service import get_field_by_id
from backend.services.satellite_service import (
    SatelliteDataError,
    get_satellite_observation,
)
from backend.services.weather_service import (
    WeatherDataError,
    get_weather_for_field,
)
from backend.services.risk_engine import assess_crop_risk
from backend.services.recommendation_engine import generate_recommendations


def get_crop_health(field_id: str) -> CropHealthResponse | None:
    """Build a crop-health response using available observations and risk rules."""

    field = get_field_by_id(field_id)

    if field is None:
        return None

    # Obtain satellite observations.
    try:
        satellite = get_satellite_observation(field_id)
    except (SatelliteDataError, ValueError):
        satellite = None

    if satellite is None:
        satellite = SatelliteObservation(
            field_id=field_id,
            data_source="satellite_data_unavailable",
            data_status="unavailable",
        )

    # Obtain weather observations.
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

    # Assess risk using both observation models.
    risk: RiskAssessment = assess_crop_risk(
        satellite=satellite,
        weather=weather,
    )

    # Generate recommendations from the assessment.
    recommendations = generate_recommendations(risk)

    return CropHealthResponse(
        field=field,
        satellite=satellite,
        weather=weather,
        risk=risk,
        recommendations=recommendations,
        generated_at=datetime.now(timezone.utc),
    )