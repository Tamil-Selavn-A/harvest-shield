from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


DataStatus = Literal["live", "cached", "synthetic", "unavailable"]


class DataSourceInfo(BaseModel):
    data_source: str
    data_status: DataStatus


class SatelliteObservation(BaseModel):
    field_id: str
    ndvi_current: float | None = None
    ndvi_previous: float | None = None
    ndvi_history: list[float] = Field(default_factory=list)
    observation_date: str | None = None
    data_source: str = "synthetic_sample"
    data_status: DataStatus = "synthetic"


class WeatherObservation(BaseModel):
    field_id: str
    temperature_c: float | None = None
    humidity_pct: float | None = None
    recent_rainfall_mm: float | None = None
    forecast: list[dict[str, Any]] = Field(default_factory=list)
    data_source: str = "synthetic_sample"
    data_status: DataStatus = "synthetic"
    observation_time: datetime | None = None


class RiskAssessment(BaseModel):
    overall_risk: Literal["low", "moderate", "high", "critical", "unknown"]
    ndvi_risk: str = "unknown"
    weather_risk: str = "unknown"
    disease_risk: str = "unknown"
    explanation: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    action: str
    priority: Literal["low", "medium", "high", "urgent"]
    reason: str
    triggers: list[str] = Field(default_factory=list)


class CropHealthResponse(BaseModel):
    field: dict[str, Any]
    satellite: SatelliteObservation
    weather: WeatherObservation
    risk: RiskAssessment
    recommendations: list[Recommendation] = Field(default_factory=list)
    generated_at: datetime
    disclaimer: str = (
        "Risk indicators support decision-making and are not a substitute "
        "for field inspection or professional agricultural advice."
    )