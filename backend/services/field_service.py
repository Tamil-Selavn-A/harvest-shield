import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIELDS_FILE = PROJECT_ROOT / "data" / "fields.json"


class FieldDataError(Exception):
    """Raised when field metadata cannot be loaded or validated."""


def load_fields() -> list[dict[str, Any]]:
    """Load and validate field metadata from the JSON dataset."""

    try:
        with FIELDS_FILE.open("r", encoding="utf-8-sig") as file:
            fields = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise FieldDataError(
            "Field metadata could not be loaded."
        ) from exc

    if not isinstance(fields, list):
        raise FieldDataError("Field metadata must be a JSON list.")

    required_fields = {
        "field_id",
        "field_name",
        "crop_type",
        "latitude",
        "longitude",
        "area_hectares",
        "data_status",
    }

    seen_ids: set[str] = set()

    for field in fields:
        if not isinstance(field, dict):
            raise FieldDataError("Every field record must be an object.")

        if not required_fields.issubset(field):
            raise FieldDataError(
                "A field record is missing required fields."
            )

        field_id = field["field_id"]

        if not isinstance(field_id, str) or not field_id.strip():
            raise FieldDataError("Field IDs must be non-empty strings.")

        if field_id in seen_ids:
            raise FieldDataError("Duplicate field IDs were detected.")

        seen_ids.add(field_id)

        if not isinstance(field["latitude"], (int, float)):
            raise FieldDataError("Field latitude must be numeric.")

        if not isinstance(field["longitude"], (int, float)):
            raise FieldDataError("Field longitude must be numeric.")

        if not -90 <= field["latitude"] <= 90:
            raise FieldDataError("Field latitude is out of range.")

        if not -180 <= field["longitude"] <= 180:
            raise FieldDataError("Field longitude is out of range.")

        if not isinstance(field["area_hectares"], (int, float)):
            raise FieldDataError("Field area must be numeric.")

        if field["area_hectares"] <= 0:
            raise FieldDataError("Field area must be positive.")

    return fields


def get_all_fields() -> list[dict[str, Any]]:
    """Return all available fields."""

    return load_fields()


def get_field_by_id(field_id: str) -> dict[str, Any] | None:
    """Return a field by ID, or None when it does not exist."""

    for field in load_fields():
        if field["field_id"] == field_id:
            return field

    return None
