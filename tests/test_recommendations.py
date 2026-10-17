from backend.schemas.health_schema import RiskAssessment
from backend.services.recommendation_engine import generate_recommendations


def make_risk(
    overall="low",
    ndvi="low",
    weather="low",
    disease="unknown",
):
    return RiskAssessment(
        overall_risk=overall,
        ndvi_risk=ndvi,
        weather_risk=weather,
        disease_risk=disease,
        explanation=[],
    )


def test_unknown_risk_recommends_collecting_observations():
    recommendations = generate_recommendations(
        make_risk(
            overall="unknown",
            ndvi="unknown",
            weather="unknown",
        )
    )

    triggers = [
        trigger
        for recommendation in recommendations
        for trigger in recommendation.triggers
    ]

    assert "risk_data_incomplete" in triggers
    assert "disease_risk_unknown" in triggers


def test_high_ndvi_risk_recommends_field_inspection():
    recommendations = generate_recommendations(
        make_risk(overall="high", ndvi="high")
    )

    assert any(
        "ndvi_risk_high" in recommendation.triggers
        and recommendation.priority == "high"
        for recommendation in recommendations
    )


def test_moderate_weather_risk_recommends_monitoring():
    recommendations = generate_recommendations(
        make_risk(overall="moderate", weather="moderate")
    )

    assert any(
        "weather_risk_moderate" in recommendation.triggers
        and recommendation.priority == "medium"
        for recommendation in recommendations
    )


def test_high_ndvi_and_weather_risks_generate_both_recommendations():
    recommendations = generate_recommendations(
        make_risk(
            overall="high",
            ndvi="high",
            weather="high",
        )
    )

    triggers = [
        trigger
        for recommendation in recommendations
        for trigger in recommendation.triggers
    ]

    assert "ndvi_risk_high" in triggers
    assert "weather_risk_high" in triggers


def test_low_risk_without_unknown_indicators_gives_routine_monitoring():
    recommendations = generate_recommendations(
        make_risk(
            overall="low",
            ndvi="low",
            weather="low",
            disease="low",
        )
    )

    assert len(recommendations) == 1
    assert recommendations[0].priority == "low"
    assert "no_elevated_configured_risk" in recommendations[0].triggers


def test_every_recommendation_has_reason_and_trigger():
    recommendations = generate_recommendations(
        make_risk(
            overall="high",
            ndvi="high",
            weather="moderate",
        )
    )

    assert recommendations

    for recommendation in recommendations:
        assert recommendation.action.strip()
        assert recommendation.reason.strip()
        assert recommendation.triggers
        assert recommendation.priority in {
            "low", "medium", "high", "urgent"
        }


def test_critical_overall_risk_generates_urgent_recommendation():
    recommendations = generate_recommendations(
        make_risk(
            overall="critical",
            ndvi="low",
            weather="low",
            disease="unknown",
        )
    )

    assert any(
        recommendation.priority == "urgent"
        and "overall_risk_critical" in recommendation.triggers
        for recommendation in recommendations
    )

def test_disease_unknown_does_not_generate_a_disease_diagnosis():
    recommendations = generate_recommendations(
        make_risk(
            overall="low",
            ndvi="low",
            weather="low",
            disease="unknown",
        )
    )

    disease_recommendations = [
        recommendation
        for recommendation in recommendations
        if "disease_risk_unknown" in recommendation.triggers
    ]

    assert len(disease_recommendations) == 1
    assert disease_recommendations[0].priority == "low"
