from backend.schemas.health_schema import (
    SatelliteObservation,
    WeatherObservation,
)
from backend.services.risk_engine import assess_crop_risk


def make_satellite(current=None, previous=None):
    return SatelliteObservation(
        field_id="TN001",
        ndvi_current=current,
        ndvi_previous=previous,
        data_status="cached",
        data_source="test",
    )


def make_weather(
    temperature=None,
    humidity=None,
    rainfall=None,
):
    return WeatherObservation(
        field_id="TN001",
        temperature_c=temperature,
        humidity_pct=humidity,
        recent_rainfall_mm=rainfall,
        data_status="cached",
        data_source="test",
    )


def test_missing_observations_produce_unknown_risk():
    result = assess_crop_risk(
        make_satellite(),
        make_weather(),
    )

    assert result.overall_risk == "unknown"
    assert result.ndvi_risk == "unknown"
    assert result.weather_risk == "unknown"
    assert result.disease_risk == "unknown"


def test_substantial_ndvi_decline_is_high():
    result = assess_crop_risk(
        make_satellite(current=0.40, previous=0.60),
        make_weather(),
    )

    assert result.ndvi_risk == "high"
    assert result.overall_risk == "high"


def test_moderate_ndvi_decline_with_complete_weather_is_moderate():
    result = assess_crop_risk(
        make_satellite(current=0.50, previous=0.58),
        make_weather(temperature=28.0, humidity=60.0, rainfall=2.0),
    )

    assert result.ndvi_risk == "moderate"
    assert result.weather_risk == "low"
    assert result.overall_risk == "moderate"


def test_no_ndvi_decline_and_normal_weather_are_low():
    result = assess_crop_risk(
        make_satellite(current=0.60, previous=0.58),
        make_weather(
            temperature=28.0,
            humidity=60.0,
            rainfall=2.0,
        ),
    )

    assert result.ndvi_risk == "low"
    assert result.weather_risk == "low"
    assert result.overall_risk == "low"
    assert result.disease_risk == "unknown"


def test_multiple_weather_signals_produce_high_weather_risk():
    result = assess_crop_risk(
        make_satellite(),
        make_weather(
            temperature=42.0,
            humidity=90.0,
            rainfall=60.0,
        ),
    )

    assert result.weather_risk == "high"
    assert result.overall_risk == "high"


def test_single_weather_signal_with_complete_satellite_is_moderate():
    result = assess_crop_risk(
        make_satellite(current=0.60, previous=0.60),
        make_weather(
            temperature=28.0,
            humidity=90.0,
            rainfall=2.0,
        ),
    )

    assert result.ndvi_risk == "low"
    assert result.weather_risk == "moderate"
    assert result.overall_risk == "moderate"


def test_incomplete_weather_without_warning_signal_is_unknown():
    result = assess_crop_risk(
        make_satellite(),
        make_weather(temperature=28.0, humidity=60.0, rainfall=None),
    )

    assert result.ndvi_risk == "unknown"
    assert result.weather_risk == "unknown"
    assert result.overall_risk == "unknown"


def test_moderate_ndvi_with_missing_weather_keeps_overall_unknown():
    result = assess_crop_risk(
        make_satellite(current=0.50, previous=0.58),
        make_weather(),
    )

    assert result.ndvi_risk == "moderate"
    assert result.weather_risk == "unknown"
    assert result.overall_risk == "unknown"

def test_invalid_ndvi_is_not_treated_as_a_valid_observation():
    result = assess_crop_risk(
        make_satellite(current=1.5, previous=0.6),
        make_weather(),
    )

    assert result.ndvi_risk == "unknown"
    assert result.overall_risk == "unknown"


def test_disease_risk_is_not_inferred_from_weather_alone():
    result = assess_crop_risk(
        make_satellite(),
        make_weather(
            temperature=42.0,
            humidity=90.0,
            rainfall=60.0,
        ),
    )

    assert result.weather_risk == "high"
    assert result.disease_risk == "unknown"
