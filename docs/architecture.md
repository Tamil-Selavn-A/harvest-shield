# Harvest Shield — System Architecture

## 1. Overview

Harvest Shield is a crop-health monitoring project that provides field metadata and an initial crop-health API response.

The current `feature/qa-docs` branch contains a FastAPI backend, JSON-based field metadata, Pydantic response schemas, and automated tests for the field and health endpoints.

The current health assessment is an initial placeholder implementation. It does not yet provide a complete, data-driven crop-health assessment.

## 2. Architecture Components

### 2.1 API Layer

File: `backend/main.py`

The API is built with FastAPI.

Responsibilities:
- Expose HTTP endpoints.
- Call the relevant service functions.
- Convert field-data errors into HTTP 500 responses.
- Return HTTP 404 when a requested field does not exist.

### 2.2 Field Service

File: `backend/services/field_service.py`

Responsibilities:
- Load field metadata from `data/fields.json`.
- Validate the dataset structure.
- Check required field properties.
- Detect duplicate field IDs.
- Validate coordinate ranges and positive field area.
- Retrieve all fields or look up a field by ID.

The field metadata file contains three demonstration records:
- TN001 — Demo Rice Field A.
- TN002 — Demo Millet Field B.
- TN003 — Demo Groundnut Field C.

These records are sample data, not verified real farms.

### 2.3 Health Service

File: `backend/services/health_service.py`

Responsibilities:
- Look up the requested field.
- Construct a crop-health response.
- Include satellite and weather placeholders.
- Return an unknown overall risk when observations are unavailable.
- Provide an explanatory message and a general recommendation.
- Include a response-generation timestamp and disclaimer.

The current implementation explicitly marks its satellite and weather observations as synthetic.

It does not currently calculate crop risk from measured satellite or weather observations.

### 2.4 Response Schemas

File: `backend/schemas/health_schema.py`

Pydantic models define the response structure for:
- Satellite observations.
- Weather observations.
- Risk assessments.
- Recommendations.
- The combined crop-health response.

The schema supports data-status labels including `live`, `cached`, `synthetic`, and `unavailable`. Supporting a status in the schema does not mean that live data integration is implemented.

## 3. Data Flow

### Field Listing

1. A client sends a request to `GET /api/fields`.
2. The API calls the field service.
3. The field service loads and validates `data/fields.json`.
4. The API returns the field count and field records.

### Crop-Health Request

1. A client requests `GET /api/health/{field_id}`.
2. The API calls `get_crop_health()` in the health service.
3. The health service looks up the field.
4. If the field exists, the service constructs a response with synthetic satellite and weather placeholders.
5. The response includes an unknown risk assessment, an explanatory message, a general recommendation, and a disclaimer.
6. If the field does not exist, the API returns HTTP 404.

## 4. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Return application information and status |
| GET | `/health` | Return API health status |
| GET | `/api/fields` | List available fields |
| GET | `/api/fields/{field_id}` | Retrieve a field by ID |
| GET | `/api/health/{field_id}` | Retrieve the initial crop-health response for a field |

The endpoint definitions are present in `backend/main.py`.

Automated tests cover field listing, retrieval of existing fields, unknown-field handling, and the crop-health response.

## 5. Satellite-Service Integration Status

The satellite NDVI service was inspected on the separate `feature/satellite-service` branch.

That branch contains:
- `backend/services/satellite_service.py`
- `data/ndvi_history.csv`
- `tests/test_satellite.py`

The service reads and validates NDVI records from a CSV file. The inspected dataset contains synthetic observations for TN001, TN002, and TN003.

The satellite service was not present in the tracked files on the `feature/qa-docs` branch when this document was prepared. The health service on that branch does not call the satellite service.

Therefore, the following capabilities must not be presented as completed on the current branch:
- Integration of NDVI observations into the health endpoint.
- Processing or downloading actual satellite imagery.
- Live satellite-data retrieval.
- Live weather-data integration.
- Risk calculations based on real observations.

The branch comparison does not itself establish whether these changes have been merged into another branch on the remote repository.

## 6. Error Handling and Data Validation

The field service checks:
- Whether the JSON file can be loaded.
- Whether the top-level dataset is a list.
- Whether required field properties exist.
- Whether field IDs are non-empty and unique.
- Whether latitude and longitude are within valid ranges.
- Whether field area is numeric and positive.

The API returns:
- HTTP 404 when a requested field is not found.
- HTTP 500 when the field service raises `FieldDataError`.

Further validation of every field property and additional integration-level error handling may be needed as the application develops.

## 7. Automated Test Evidence

Environment observed during testing:
- Python 3.13.1
- Pytest 9.1.1

On `feature/qa-docs`, the command `python -m pytest -v` completed with:

- 7 tests passed.
- 1 Starlette deprecation warning.
- No test failures.

The seven tests covered the field and health APIs.

A separate run on `feature/satellite-service` completed with 15 tests passed and the same deprecation warning. That result includes the satellite tests and must not be attributed to `feature/qa-docs`.

These results record the observed state at the time of testing; they do not establish that every feature has been tested.

## 8. Known Limitations

1. Field records are demonstration data.
2. The health service returns synthetic satellite and weather placeholders.
3. The overall risk is reported as unknown.
4. The health service does not currently use the separate NDVI service on the inspected branches.
5. Actual satellite imagery processing has not been demonstrated.
6. Live weather integration has not been demonstrated.
7. The Starlette test client emits a deprecation warning in the tested environment.
8. Dependency installation instructions and deployment readiness have not yet been verified.

## 9. Future Integration Work

Potential follow-up work, subject to team agreement:
- Integrate the satellite service with the health service.
- Connect a weather-data provider.
- Define and validate risk-assessment rules.
- Expand integration and error-handling tests.
- Document dependency installation and application startup.
- Verify deployment requirements and target-platform access.

These are follow-up tasks, not claims of completed functionality.

## 10. Disclaimer

Crop-health indicators and recommendations are intended to support decision-making. They are not a substitute for field inspection or professional agricultural advice.
