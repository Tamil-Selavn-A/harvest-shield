"""Interpretable recommendations based on crop risk assessments."""

from __future__ import annotations

from backend.schemas.health_schema import Recommendation, RiskAssessment


def generate_recommendations(
    risk: RiskAssessment,
) -> list[Recommendation]:
    """Generate cautious, explainable actions from an existing risk assessment.

    Recommendations support field monitoring and data collection.
    They do not diagnose disease or prescribe crop treatments.
    """

    recommendations: list[Recommendation] = []

    # A supplied critical assessment requires an urgent field assessment.
    if risk.overall_risk == "critical":
        recommendations.append(
            Recommendation(
                action=(
                    "Arrange an urgent field assessment and verify the observations "
                    "before making crop-specific treatment decisions."
                ),
                priority="urgent",
                reason=(
                    "The supplied overall assessment is critical. Confirm the "
                    "underlying observations and seek qualified agricultural advice promptly."
                ),
                triggers=["overall_risk_critical"],
            )
        )


    # Missing or incomplete information should prompt data collection.
    if (
        risk.overall_risk == "unknown"
        or risk.ndvi_risk == "unknown"
        or risk.weather_risk == "unknown"
    ):
        recommendations.append(
            Recommendation(
                action=(
                    "Collect or verify current satellite and weather observations."
                ),
                priority="medium",
                reason=(
                    "One or more risk indicators are unknown, so the available "
                    "information is insufficient for a complete assessment."
                ),
                triggers=["risk_data_incomplete"],
            )
        )

    # A substantial NDVI decline is a screening signal, not a diagnosis.
    if risk.ndvi_risk == "high":
        recommendations.append(
            Recommendation(
                action=(
                    "Inspect the field and verify the satellite observation "
                    "to investigate the substantial NDVI decline."
                ),
                priority="high",
                reason=(
                    "A substantial NDVI decline was detected. Field inspection "
                    "can help determine whether a real crop-health issue exists."
                ),
                triggers=["ndvi_risk_high"],
            )
        )
    elif risk.ndvi_risk == "moderate":
        recommendations.append(
            Recommendation(
                action=(
                    "Monitor crop condition and compare the next valid "
                    "satellite observation."
                ),
                priority="medium",
                reason=(
                    "A moderate NDVI decline was detected and should be "
                    "checked for persistence."
                ),
                triggers=["ndvi_risk_moderate"],
            )
        )

    # Broad weather screening signals lead to monitoring, not disease treatment.
    if risk.weather_risk == "high":
        recommendations.append(
            Recommendation(
                action=(
                    "Check field conditions promptly, including crop stress "
                    "and drainage where relevant."
                ),
                priority="high",
                reason=(
                    "Multiple configured weather screening signals were "
                    "detected. Their actual effect depends on local field conditions."
                ),
                triggers=["weather_risk_high"],
            )
        )
    elif risk.weather_risk == "moderate":
        recommendations.append(
            Recommendation(
                action=(
                    "Monitor local weather and inspect the field for "
                    "conditions that may affect crop health."
                ),
                priority="medium",
                reason=(
                    "A weather screening signal was detected. Field observations "
                    "are needed to determine whether action is necessary."
                ),
                triggers=["weather_risk_moderate"],
            )
        )

    # Never recommend disease treatment solely from these general indicators.
    if risk.disease_risk == "unknown":
        recommendations.append(
            Recommendation(
                action=(
                    "Do not infer a disease diagnosis from these indicators; "
                    "seek qualified agricultural advice if symptoms are observed."
                ),
                priority="low",
                reason=(
                    "Disease risk is unknown because validated crop-specific "
                    "disease observations and rules are not integrated."
                ),
                triggers=["disease_risk_unknown"],
            )
        )

    # Provide a useful response even when no screening concern is detected.
    if not recommendations:
        recommendations.append(
            Recommendation(
                action=(
                    "Continue routine crop monitoring and update observations "
                    "when new data becomes available."
                ),
                priority="low",
                reason=(
                    "No configured elevated risk indicator was identified "
                    "in the supplied assessment."
                ),
                triggers=["no_elevated_configured_risk"],
            )
        )

    return recommendations
