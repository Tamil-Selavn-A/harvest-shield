# Harvest Shield — System Architecture

## 1. Overview

Harvest Shield is a crop-health monitoring prototype that combines field metadata, satellite-related observations, weather observations, preliminary risk assessment, and recommendations through a FastAPI backend.

The current implementation is a prototype using demonstration field records and synthetic CSV-based NDVI observations. The weather service can use provider data, cached data, synthetic fallback data, or report unavailable data depending on availability.

**Important:** Synthetic observations are not verified measurements from real farms or live satellite imagery. Risk thresholds are preliminary screening rules and have not been scientifically validated for individual crops or regions. The system does not diagnose crop diseases.

## 2. Architecture Components

### 2.1 API Layer

File: `backend/main.py`

The API uses FastAPI to expose HTTP endpoints and delegate work to service functions.

Responsibilities include:
- Exposing field and crop-health endpoints.
- Returning structured responses.
- Handling unknown field IDs.
- Providing API health and interactive documentation endpoints.

### 2.2 Field Service

File: `backend/services/field_service.py`

The field service loads and validates field metadata from `data/fields.json`.

Responsibilities include:
- Validating the dataset structure and required properties.
- Checking field IDs for uniqueness.
- Validating coordinate ranges and positive field area.
- Retrieving all fields or looking up a field by ID.

The demonstration dataset includes:
- TN001 — Demo Rice Field A.
- TN002 — Demo Millet Field B.
- TN003 — Demo Groundnut Field C.

These records are sample data, not verified real farms.

### 2.3 Satellite Service

File: `backend/services/satellite_service.py`

The satellite service reads and validates NDVI history from `data/ndvi_history.csv`.

The current dataset contains synthetic observations. This service does not establish that actual satellite imagery is downloaded, processed, or converted into NDVI measurements.

### 2.4 Weather Service

File: `backend/services/weather_service.py`

The weather service obtains observations for a field and labels their data status. Depending on the service path and data availability, results may be live-labelled, cached, synthetic, or unavailable.

A `live` status describes the service's reported data source; it should not be interpreted as a guarantee that all observations are accurate or that the provider is always reachable.

### 2.5 Risk Engine

File: `backend/services/risk_engine.py`

The risk engine evaluates available satellite and weather observations using preliminary rule-based thresholds.

The result includes an overall risk level, separate NDVI and weather risk indicators, a disease-risk status, and explanatory messages.

These thresholds are screening rules for the prototype, not scientifically validated crop-specific predictions.

Disease risk must not be interpreted as a confirmed diagnosis.

### 2.6 Recommendation Engine

File: `backend/services/recommendation_engine.py`

The recommendation engine produces suggested actions based on the risk assessment.

Recommendations are intended to support further monitoring and decision-making. They are not a substitute for field inspection or qualified agricultural advice.

### 2.7 Health Service

File: `backend/services/health_service.py`

The health service coordinates the field, satellite, weather, risk, and recommendation services.

For an existing field, it assembles a crop-health response containing:
- Field metadata.
- Satellite observations and data-status information.
- Weather observations and data-status information.
- Risk indicators and explanations.
- Recommendations.
- A generation timestamp and disclaimer.

Unavailable observations should be represented explicitly rather than presented as verified measurements.

### 2.8 Response Schemas

File: `backend/schemas/health_schema.py`

Pydantic models define the response structure for field-related data, satellite observations, weather observations, risk assessments, recommendations, and the combined crop-health response.

Supported data-status values can include `live`, `cached`, `synthetic`, and `unavailable`. The presence of a status in the schema does not independently verify the origin or accuracy of the data.

## 3. Data Flow

### Field Listing

1. A client requests `GET /api/fields`.
2. The API invokes the field service.
3. The field service loads and validates `data/fields.json`.
4. The API returns the available field records.

### Crop-Health Request

1. A client requests `GET /api/health/{field_id}`.
2. The API invokes `get_crop_health()` in the health service.
3. The health service looks up the field.
4. The satellite service and weather service attempt to obtain observations.
5. The risk engine evaluates the available observations.
6. The recommendation engine generates recommendations from the assessment.
7. The health service assembles the response with data-status labels, timestamp, and disclaimer.
8. An unknown field is handled as a not-found request.

The result depends on the available observations and the behavior of each service. Missing data must not be represented as a confirmed healthy condition.

## 4. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Return application information and status |
| GET | `/health` | Return API health status |
| GET | `/api/fields` | List available fields |
| GET | `/api/fields/{field_id}` | Retrieve a field by ID |
| GET | `/api/health/{field_id}` | Retrieve a crop-health response |

Confirm endpoint behavior against `backend/main.py` before relying on this table for a release.

FastAPI interactive documentation is available at `/docs` while the server is running.

## 5. Data Sources and Limitations

### Satellite-related data
- NDVI history is read from a CSV dataset.
- The current sample observations are synthetic.
- Live satellite imagery acquisition and image-derived NDVI processing have not been demonstrated.

### Weather data
- The service supports different data-source and fallback paths.
- The reported source and status should be inspected in each response.
- Provider availability and observation accuracy are not guaranteed.

### Risk and recommendations
- Thresholds are preliminary screening rules.
- Crop-specific validation has not been established.
- Disease diagnosis is not implemented.
- Recommendations are not validated agricultural prescriptions.

### Field records
- Field metadata is demonstration data.
- The sample records do not establish the existence or condition of real farms.

## 6. Error Handling and Validation

The field service validates dataset structure, required properties, field IDs, coordinates, and field area.

The API should distinguish an unknown field from service failures and unavailable observations. Error responses should not expose credentials or other sensitive configuration.

Integration tests should cover missing fields, unavailable data sources, invalid data, and service exceptions.

## 7. Testing

Run the test suite from the repository root:

```powershell
python -m pytest -q
```

The result must be recorded from a fresh run on the exact branch being evaluated.

Historical test results from other branches are not evidence that the current integrated branch passes. Record failures and warnings as well as the number of passing tests.

## 8. Deployment and Operations

Before deployment:
- Install dependencies using the project's verified dependency instructions.
- Run the automated tests.
- Verify required configuration and environment variables.
- Confirm the application starts successfully.
- Check that the dashboard and backend use the correct service URL.
- Validate behavior when external data providers are unavailable.
- Verify the intended LinuxONE environment and deployment requirements.

Deployment readiness must not be claimed until the target environment has been tested.

## 9. Future Improvements

Potential future work includes:
- Integrating verified satellite imagery and documented NDVI processing.
- Validating crop-specific thresholds with appropriate agricultural expertise.
- Improving data provenance and observation timestamps.
- Expanding integration tests and monitoring.
- Completing and verifying the dashboard integration.
- Validating deployment on the target platform.

## 10. Disclaimer

Harvest Shield is a prototype for crop-health monitoring and decision support. Its outputs are not confirmed agricultural diagnoses, and its recommendations do not replace field inspection or professional agricultural advice.
