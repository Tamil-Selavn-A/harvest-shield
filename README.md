# Harvest Shield

Harvest Shield is an early-stage crop-health monitoring API prototype. It brings sample field metadata together with weather observations and returns a structured response intended to help users understand what information is available and where field inspection may be useful.

> **Current scope:** The checked-in application is a FastAPI backend. This repository does not currently contain a Streamlit dashboard, satellite data integration, or a calculated crop-risk model. Health responses explicitly report risk as `unknown` while those inputs and calculations are unavailable.

## What is implemented

- Field metadata loaded from `data/fields.json`.
- A field-list endpoint and endpoints for retrieving one field and its health response.
- Weather retrieval that tries Open-Meteo, then a coordinate-matched cached CSV observation, then labelled synthetic sample data. If no usable observation is available, the response labels weather `unavailable`.
- Explicit weather source and status fields (`live`, `cached`, `synthetic`, or `unavailable`).
- Structured health responses with explanations, a cautious recommendation, generation time, and a disclaimer.
- Automated pytest coverage for field endpoints, health response structure, weather mapping, and selected fallback cases.

## Architecture and request flow

```text
HTTP client
    |
    v
FastAPI routes (backend/main.py)
    |                         \
    v                          v
Field service              Health service
    |                         |       \
    v                         v        v
fields.json             field metadata  Weather service
                                          |     |      |
                                          v     v      v
                                      Open-Meteo  CSV  synthetic JSON
```

`GET /api/health/{field_id}` looks up the field, requests weather through the weather service, and combines those results with the current satellite placeholder, risk explanation, recommendation, and disclaimer. Field data errors are returned by the API as HTTP 500 responses; unknown fields return HTTP 404.

The code is organized as follows:

- `backend/main.py` — FastAPI app and HTTP routes.
- `backend/services/field_service.py` — field JSON loading and validation.
- `backend/services/weather_service.py` — live weather request and cached, synthetic, or unavailable fallbacks.
- `backend/services/health_service.py` — assembles the health response; risk is currently unknown.
- `backend/schemas/health_schema.py` — Pydantic response models and data-status types.
- `data/fields.json` — sample field metadata.
- `data/open_meteo_weather.csv` — cached weather data.
- `data/weather_sample.json` — labelled synthetic weather examples.
- `tests/` — pytest tests for fields, health, and weather behavior.

## Requirements

- Python 3.10 or newer (the code uses modern union type syntax such as `str | None`).
- `pip`.
- Network access for a live Open-Meteo weather request. The service uses a five-second request timeout and has offline fallbacks.

There is currently no `requirements.txt` or `pyproject.toml` in the repository. Install the packages used by the application and tests explicitly as shown below.

## Setup

Run these commands from the repository root.

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install fastapi "uvicorn[standard]" pytest httpx
```

If PowerShell blocks activation, you can invoke the virtual environment's Python directly instead:

```powershell
.\.venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" pytest httpx
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install fastapi 'uvicorn[standard]' pytest httpx
```

`httpx` is used by FastAPI's `TestClient` in the test suite. The repository ignores `.venv/` and Python cache files.

## Run the API

From the repository root, with the environment activated:

```bash
python -m uvicorn backend.main:app --reload
```

The development server listens at `http://127.0.0.1:8000` by default. Open `http://127.0.0.1:8000/docs` for the interactive OpenAPI page. Stop the development server with `Ctrl+C`.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Basic application identity and status. |
| `GET` | `/health` | API process health response. |
| `GET` | `/api/fields` | List available sample fields and return a count. |
| `GET` | `/api/fields/{field_id}` | Retrieve one field; returns 404 for an unknown ID. |
| `GET` | `/api/health/{field_id}` | Retrieve field metadata, satellite and weather status, risk explanation, recommendation, and disclaimer. Returns 404 for an unknown ID. |

Example requests:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/fields
curl http://127.0.0.1:8000/api/fields/TN001
curl http://127.0.0.1:8000/api/health/TN001
```

Example health response shape (weather values and timestamps can vary depending on the selected source):

```json
{
  "field": {
    "field_id": "TN001",
    "field_name": "Demo Rice Field A",
    "crop_type": "rice",
    "latitude": 11.0168,
    "longitude": 76.9558,
    "area_hectares": 2.0,
    "data_status": "sample"
  },
  "satellite": {
    "field_id": "TN001",
    "ndvi_current": null,
    "ndvi_previous": null,
    "ndvi_history": [],
    "observation_date": null,
    "data_source": "synthetic_sample",
    "data_status": "synthetic"
  },
  "weather": {
    "field_id": "TN001",
    "temperature_c": 29.4,
    "humidity_pct": 71.0,
    "recent_rainfall_mm": 2.5,
    "forecast": [],
    "data_source": "synthetic_sample",
    "data_status": "synthetic",
    "observation_time": "2026-10-17T09:00:00+05:30"
  },
  "risk": {
    "overall_risk": "unknown",
    "ndvi_risk": "unknown",
    "weather_risk": "unknown",
    "disease_risk": "unknown",
    "explanation": [
      "Satellite observations have not yet been integrated.",
      "Weather observations have not yet been integrated.",
      "Crop risk cannot be assessed reliably without observations."
    ]
  },
  "recommendations": [
    {
      "action": "Collect current satellite and weather observations.",
      "priority": "medium",
      "reason": "Risk assessment is unavailable until the required observations are integrated.",
      "triggers": ["satellite_data_unavailable", "weather_data_unavailable"]
    }
  ],
  "generated_at": "<generated UTC timestamp>",
  "disclaimer": "Risk indicators support decision-making and are not a substitute for field inspection or professional agricultural advice."
}
```

The example illustrates the response structure and a synthetic weather record. It is not a promise that the live API will return those same weather values or timestamp.

## Data provenance and missing data

- **Field metadata:** The three records in `data/fields.json` are explicitly demo/sample fields. They are not evidence of enrolled farms or customer data.
- **Live weather:** The weather service requests current conditions and forecast data from Open-Meteo using each field's coordinates. A successful provider response is labelled `data_status: "live"` and `data_source: "open-meteo"`. The service does not guarantee provider availability.
- **Cached weather:** `data/open_meteo_weather.csv` is labelled `cached` by the service. It is used only when the CSV's coordinates are within 0.01 degrees of the requested field's coordinates. In the checked-in sample dataset, the CSV location does not match the three sample field locations, so it will not serve as their fallback without updated matching data.
- **Synthetic weather:** `data/weather_sample.json` contains illustrative values labelled `synthetic`. These values are for demonstration and must not be presented as observed field conditions.
- **Unavailable weather:** If live retrieval fails and no matching cache or valid synthetic record is available, weather values are returned as `null` (and forecast as an empty list) with `data_status: "unavailable"`.
- **Satellite data:** No satellite provider or observation dataset is integrated. Satellite values are null or empty and labelled synthetic.
- **Risk:** No risk score is currently calculated from weather or vegetation indicators. Health responses use `unknown` risk levels and explain the missing inputs.

## Run tests

From the repository root with the environment activated:

```bash
python -m pytest -q
```

The test suite uses mocked provider responses for weather-provider cases, so those tests do not require a working Open-Meteo connection. The field and health tests also use the checked-in sample field data. Record the actual pytest output when reporting a test result; this README does not assert that tests have been run in your environment.

## Limitations and deployment status

- This is a prototype API, not a complete end-user dashboard.
- Satellite observations, NDVI trends, disease detection, and calculated risk levels are not implemented.
- The current recommendation is a fixed, cautious data-collection suggestion; it is not tailored using a computed risk assessment.
- Sample fields and synthetic weather values are illustrative. Cached weather is location-specific and does not match the checked-in demo fields.
- No dashboard-to-API integration is present in this repository.
- IBM LinuxONE access, compatibility testing, and deployment have not been verified by the checked-in project files. Do not describe the application as deployed there until an actual deployment and smoke test have been recorded.
- No production deployment configuration, dependency lock file, or operational monitoring setup is included.

## Suggested demo flow

1. Start the API and confirm `/health` returns `"status": "healthy"`.
2. Call `/api/fields` and select a sample field such as `TN001`.
3. Call `/api/health/TN001` and point out the source/status labels for weather and satellite data.
4. Explain that the risk is `unknown`, because satellite observations and risk calculations are not implemented. Show the recommendation as a prompt to collect observations, not a diagnosis.
5. If live weather is unavailable, show the returned `synthetic` or `unavailable` status and explain which values are illustrative or missing.

## Contributing

Keep documentation and demo claims aligned with the code and data sources. Before adding an integration or changing API response contracts, coordinate with the member responsible for that component. Never commit credentials or real farm data without the team's approval and appropriate safeguards.
