# Harvest Shield — Demo Script

## 1. Demo Objective

Demonstrate the Harvest Shield FastAPI backend, sample field metadata, satellite-related observations, weather observations, preliminary risk assessment, recommendations, error handling, and interactive API documentation.

Harvest Shield is a prototype. Its satellite NDVI history uses synthetic sample data, and its risk rules are preliminary screening rules rather than scientifically validated crop-specific predictions.

Do not describe synthetic satellite observations as live satellite imagery or present risk indicators as confirmed agricultural diagnoses.

## 2. Start the Backend

Open PowerShell at the repository root — the directory containing `backend`, `data`, and `tests`.

If you need to navigate to your own repository, use your actual local path. For example:

```powershell
cd "C:\Users\TAMIL\projects\harvest-shield"
```

If your project uses a virtual environment, activate it using the environment's actual path.

Start the API:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Keep the terminal running while performing the demo.

If port 8000 is already occupied by the intended application, reuse that server instead of starting a duplicate instance.

If startup fails, resolve the error before continuing.

## 3. Demonstrate API Health

Open the following address in a browser:

http://127.0.0.1:8000/health

Expected result: the API returns its health-status response.

Explain that this endpoint checks whether the backend is responding. It does not establish that external data providers are available.

## 4. Demonstrate the Field List

Open:

http://127.0.0.1:8000/api/fields

Expected result: the API returns the available sample field records.

The demonstration dataset includes:
- TN001 — Demo Rice Field A
- TN002 — Demo Millet Field B
- TN003 — Demo Groundnut Field C

Explain that these are demonstration records loaded from the project's local field dataset, not verified real farms.

## 5. Demonstrate Crop Health

Open:

http://127.0.0.1:8000/api/health/TN001

Inspect the returned JSON.

The integrated response can include:
- Field metadata.
- Satellite-related observations and data-status labels.
- Weather observations and data-status labels.
- Overall, NDVI, weather, and disease-risk indicators.
- Explanations and recommendations.
- A response-generation timestamp and disclaimer.

Explain the data limitations accurately:

- Satellite NDVI history currently uses synthetic CSV-based observations.
- Weather status depends on the actual data source and fallback path used for the request.
- Risk thresholds are preliminary screening rules.
- Disease risk is not a confirmed diagnosis.
- Recommendations are suggestions for monitoring and further assessment, not validated agricultural prescriptions.

Do not promise a fixed risk level or exact response values. They can depend on the available observations and service behavior.

## 6. Demonstrate an Unknown Field

Open:

http://127.0.0.1:8000/api/health/UNKNOWN999

Expected result: the API should return HTTP 404 for an unknown field, provided the application is running the expected implementation.

Explain that the service should not return a valid crop-health assessment for a field that does not exist in its dataset.

## 7. Demonstrate Interactive API Documentation

Open:

http://127.0.0.1:8000/docs

FastAPI should display its interactive API documentation.

Demonstrate how a developer can:
- Inspect the available endpoints.
- Review their response structures.
- Try supported requests.
- Inspect HTTP status codes and JSON responses.

## 8. Run Automated Tests

Stop the server only if necessary; otherwise, use another PowerShell terminal at the repository root.

Run:

```powershell
python -m pytest -q
```

Record the actual result from the current branch.

Do not reuse historical test counts as evidence of the current branch's status. Record failures and warnings honestly, and investigate failures before presenting the project as passing.

## 9. Current Limitations

- Field metadata is demonstration data.
- Satellite NDVI history is synthetic; actual satellite imagery processing has not been demonstrated.
- Weather observations may depend on provider availability and fallback behavior.
- Risk thresholds are preliminary and not scientifically validated crop-specific predictions.
- Disease diagnosis is not implemented.
- The dashboard and deployment target must be verified separately.
- A passing backend test suite does not, by itself, prove deployment readiness or end-to-end dashboard integration.

## 10. Suggested Demo Closing

Harvest Shield demonstrates a prototype workflow for combining field metadata, satellite-related observations, weather information, preliminary risk indicators, and recommendations through an API.

The next improvements include validating risk rules with appropriate agricultural expertise, integrating verified satellite observations, expanding integration testing, and verifying the dashboard and target-platform deployment.

All outputs should be treated as decision-support demonstrations, not confirmed agricultural diagnoses.
