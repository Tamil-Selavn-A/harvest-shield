from backend.services.health_service import get_crop_health
from fastapi import FastAPI, HTTPException

from backend.services.field_service import (
    FieldDataError,
    get_all_fields,
    get_field_by_id,
)


app = FastAPI(
    title="Harvest Shield API",
    description="Crop-health monitoring and risk-assessment platform",
    version="0.2.0",
)


@app.get("/")
def root():
    return {
        "application": "Harvest Shield",
        "message": "Crop-health monitoring API",
        "status": "running",
        "version": "0.2.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "harvest-shield-api",
    }


@app.get("/api/fields")
def list_fields():
    try:
        fields = get_all_fields()
    except FieldDataError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    return {
        "count": len(fields),
        "fields": fields,
    }


@app.get("/api/fields/{field_id}")
def retrieve_field(field_id: str):
    try:
        field = get_field_by_id(field_id)
    except FieldDataError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    if field is None:
        raise HTTPException(
            status_code=404,
            detail=f"Field '{field_id}' was not found.",
        )

    return field

@app.get("/api/health/{field_id}")
def retrieve_crop_health(field_id: str):
    try:
        result = get_crop_health(field_id)
    except FieldDataError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Field '{field_id}' was not found.",
        )

    return result