import csv
import math
from datetime import date
from pathlib import Path

from backend.schemas.health_schema import SatelliteObservation
from backend.services.field_service import (
    FieldDataError,
    get_field_by_id,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NDVI_HISTORY_FILE = PROJECT_ROOT / "data" / "ndvi_history.csv"

REQUIRED_COLUMNS = {
    "field_id",
    "observation_date",
    "ndvi",
    "data_source",
    "data_status",
}


class SatelliteDataError(Exception):
    """Raised when satellite observation data cannot be loaded or validated."""


def load_ndvi_history() -> list[dict]:
    """Load and validate NDVI observations from the CSV dataset."""

    try:
        with NDVI_HISTORY_FILE.open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            reader = csv.DictReader(file)

            if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(
                reader.fieldnames
            ):
                raise SatelliteDataError(
                    "NDVI history is missing required columns."
                )

            observations = []

            for row_number, row in enumerate(reader, start=2):
                field_id = (row.get("field_id") or "").strip()
                date_text = (row.get("observation_date") or "").strip()
                ndvi_text = (row.get("ndvi") or "").strip()
                data_source = (row.get("data_source") or "").strip()
                data_status = (row.get("data_status") or "").strip()

                if not all(
                    [field_id, date_text, data_source, data_status]
                ):
                    raise SatelliteDataError(
                        f"Required value missing on CSV row {row_number}."
                    )

                try:
                    observation_date = date.fromisoformat(date_text)
                except ValueError as exc:
                    raise SatelliteDataError(
                        f"Invalid observation date on CSV row {row_number}."
                    ) from exc

                ndvi = None

                if ndvi_text:
                    try:
                        ndvi = float(ndvi_text)
                    except ValueError as exc:
                        raise SatelliteDataError(
                            f"Invalid NDVI value on CSV row {row_number}."
                        ) from exc

                    if not math.isfinite(ndvi) or not -1 <= ndvi <= 1:
                        raise SatelliteDataError(
                            f"NDVI value out of range on CSV row {row_number}."
                        )

                if data_status not in {
                    "live",
                    "cached",
                    "synthetic",
                    "unavailable",
                }:
                    raise SatelliteDataError(
                        f"Invalid data status on CSV row {row_number}."
                    )

                observations.append(
                    {
                        "field_id": field_id,
                        "observation_date": observation_date,
                        "ndvi": ndvi,
                        "data_source": data_source,
                        "data_status": data_status,
                    }
                )

    except OSError as exc:
        raise SatelliteDataError(
            "NDVI history could not be loaded."
        ) from exc

    return observations


def get_satellite_observation(
    field_id: str,
) -> SatelliteObservation | None:
    """Return the available NDVI observation summary for a known field."""

    try:
        field = get_field_by_id(field_id)
    except FieldDataError:
        raise

    if field is None:
        return None

    observations = [
        observation
        for observation in load_ndvi_history()
        if observation["field_id"] == field_id
    ]

    observations.sort(key=lambda item: item["observation_date"])

    if not observations:
        return SatelliteObservation(
            field_id=field_id,
            data_source="synthetic_sample",
            data_status="unavailable",
        )

    measured_observations = [
        observation
        for observation in observations
        if observation["ndvi"] is not None
    ]

    latest_observation = observations[-1]
    latest_measurement = (
        measured_observations[-1] if measured_observations else None
    )
    previous_measurement = (
        measured_observations[-2]
        if len(measured_observations) >= 2
        else None
    )

    data_status = latest_observation["data_status"]
    if any(
        observation["data_status"] != data_status
        for observation in observations
    ):
        data_status = "cached"

    return SatelliteObservation(
        field_id=field_id,
        ndvi_current=(
            latest_measurement["ndvi"] if latest_measurement else None
        ),
        ndvi_previous=(
            previous_measurement["ndvi"] if previous_measurement else None
        ),
        ndvi_history=[
            observation["ndvi"] for observation in measured_observations
        ],
        observation_date=latest_observation[
            "observation_date"
        ].isoformat(),
        data_source=latest_observation["data_source"],
        data_status=data_status,
    )
