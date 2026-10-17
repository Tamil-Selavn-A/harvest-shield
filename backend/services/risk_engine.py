"""Interpretable, rule-based crop risk assessment."""

from __future__ import annotations

from backend.schemas.health_schema import (
    RiskAssessment,
    SatelliteObservation,
    WeatherObservation,
)


def assess_crop_risk(
    satellite: SatelliteObservation,
    weather: WeatherObservation,
) -> RiskAssessment:
    """Assess available indicators without treating missing data as healthy.

    This initial implementation uses conservative, general-purpose indicators.
    It does not diagnose crop disease or replace field inspection.
    """

    explanations: list[str] = []
    ndvi_risk = "unknown"
    weather_risk = "unknown"
    disease_risk = "unknown"

    # Satellite indicator: compare current NDVI with the previous observation.
    current = satellite.ndvi_current
    previous = satellite.ndvi_previous

    if (
        current is not None
        and previous is not None
        and -1.0 <= current <= 1.0
        and -1.0 <= previous <= 1.0
    ):
        change = current - previous

        if change <= -0.15:
            ndvi_risk = "high"
            explanations.append(
                "NDVI decreased substantially compared with the previous observation."
            )
        elif change <= -0.05:
            ndvi_risk = "moderate"
            explanations.append(
                "NDVI decreased compared with the previous observation."
            )
        else:
            ndvi_risk = "low"
            explanations.append(
                "No substantial NDVI decline was detected between these observations."
            )
    else:
        explanations.append(
            "NDVI risk is unknown because valid current and previous observations "
            "are not both available."
        )

    # Weather indicators: use only broad screening rules, not crop-specific
    # disease thresholds. These rules should be reviewed before production use.
    temperature = weather.temperature_c
    humidity = weather.humidity_pct
    rainfall = weather.recent_rainfall_mm

    valid_temperature = (
        temperature is not None and -50.0 <= temperature <= 65.0
    )
    valid_humidity = humidity is not None and 0.0 <= humidity <= 100.0
    valid_rainfall = rainfall is not None and rainfall >= 0.0

    weather_complete = (
        valid_temperature and valid_humidity and valid_rainfall
    )
    weather_signals: list[str] = []

    if valid_temperature and (temperature < 5.0 or temperature > 40.0):
        weather_signals.append(
            "Temperature is at an extreme value that may stress some crops."
        )

    if valid_humidity and humidity >= 85.0:
        weather_signals.append(
            "High relative humidity may warrant monitoring for crop-health issues."
        )

    if valid_rainfall and rainfall >= 50.0:
        weather_signals.append(
            "Reported rainfall is high; check local drainage and field conditions."
        )

    explanations.extend(weather_signals)

    if not weather_complete:
        explanations.append(
            "Weather observations are incomplete; missing or invalid measurements"
            " are not treated as normal."
        )

    if len(weather_signals) >= 2:
        weather_risk = "high"
    elif len(weather_signals) == 1:
        weather_risk = "moderate"
    elif weather_complete:
        weather_risk = "low"
        explanations.append(
            "No configured broad weather screening signal was detected."
        )
    else:
        weather_risk = "unknown"
        explanations.append(
            "Weather risk is unknown because some measurements are missing or"
            " invalid, and no elevated signal was detected in the available measurements."
        )

    # Disease risk remains unknown: these general indicators cannot diagnose disease.
    explanations.append(
        "Disease risk remains unknown because crop-specific disease observations "
        "and validated disease rules are not integrated."
    )

    known_risks = [
        risk for risk in (ndvi_risk, weather_risk)
        if risk != "unknown"
    ]

    if "high" in known_risks:
        overall_risk = "high"
    elif ndvi_risk == "unknown" or weather_risk == "unknown":
        overall_risk = "unknown"
        explanations.append(
            "Overall risk is unknown because at least one key vegetation or"
            " weather indicator could not be assessed."
        )
    elif "moderate" in known_risks:
        overall_risk = "moderate"
    else:
        overall_risk = "low"
    return RiskAssessment(
        overall_risk=overall_risk,
        ndvi_risk=ndvi_risk,
        weather_risk=weather_risk,
        disease_risk=disease_risk,
        explanation=explanations,
    )
