import pytest

from backend.services.satellite_service import (
    SatelliteDataError,
    get_satellite_observation,
    load_ndvi_history,
)


def test_load_ndvi_history_reads_all_records():
    assert len(load_ndvi_history()) == 9


def test_tn001_returns_expected_ndvi():
    result = get_satellite_observation("TN001")

    assert result is not None
    assert result.ndvi_current == pytest.approx(0.71)
    assert result.ndvi_previous == pytest.approx(0.68)
    assert result.data_status == "synthetic"


def test_tn003_handles_missing_ndvi():
    result = get_satellite_observation("TN003")

    assert result is not None
    assert result.ndvi_current == pytest.approx(0.50)
    assert result.ndvi_previous == pytest.approx(0.44)
    assert result.ndvi_history == pytest.approx([0.44, 0.50])


def test_unknown_field_returns_none():
    assert get_satellite_observation("UNKNOWN") is None


def test_invalid_ndvi_value_raises_error(monkeypatch, tmp_path):
    import backend.services.satellite_service as satellite_service

    csv_file = tmp_path / "invalid_ndvi.csv"
    csv_file.write_text(
        "field_id,observation_date,ndvi,data_source,data_status\n"
        "TN001,2026-10-01,1.5,synthetic_sample,synthetic\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        satellite_service,
        "NDVI_HISTORY_FILE",
        csv_file,
    )

    with pytest.raises(SatelliteDataError):
        satellite_service.load_ndvi_history()


def test_invalid_observation_date_raises_error(monkeypatch, tmp_path):
    import backend.services.satellite_service as satellite_service

    csv_file = tmp_path / "invalid_date.csv"
    csv_file.write_text(
        "field_id,observation_date,ndvi,data_source,data_status\n"
        "TN001,2026-99-45,0.7,synthetic_sample,synthetic\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        satellite_service,
        "NDVI_HISTORY_FILE",
        csv_file,
    )

    with pytest.raises(SatelliteDataError):
        satellite_service.load_ndvi_history()


def test_missing_required_value_raises_error(monkeypatch, tmp_path):
    import backend.services.satellite_service as satellite_service

    csv_file = tmp_path / "missing_value.csv"
    csv_file.write_text(
        "field_id,observation_date,ndvi,data_source,data_status\n"
        "TN001,2026-10-01,0.7,,synthetic\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        satellite_service,
        "NDVI_HISTORY_FILE",
        csv_file,
    )

    with pytest.raises(SatelliteDataError):
        satellite_service.load_ndvi_history()


def test_malformed_csv_row_raises_error(monkeypatch, tmp_path):
    import backend.services.satellite_service as satellite_service

    csv_file = tmp_path / "malformed.csv"
    csv_file.write_text(
        "field_id,observation_date,ndvi,data_source,data_status\n"
        "TN001,2026-10-01,0.7,synthetic_sample\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        satellite_service,
        "NDVI_HISTORY_FILE",
        csv_file,
    )

    with pytest.raises(SatelliteDataError):
        satellite_service.load_ndvi_history()
