# Harvest Shield - Demo Script



## 1. Objective



Demonstrate the Harvest Shield FastAPI backend, field metadata, crop-health response, error handling, and interactive API documentation.



This demo documents the implementation on the feature/qa-docs branch.



IMPORTANT: Live satellite imagery, live weather observations, and reliable real-time agricultural risk assessment are not currently integrated. The health response uses synthetic placeholder data.



## 2. Start the Backend



Open PowerShell at the repository root:



C:\\Users\\harik\\Projects\\harvest-shield-copy



Run this command:



python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000



Keep the terminal running while performing the demo.



If the server is already running on port 8000, do not start a second instance.



## 3. Demo the API Health Check



Open this address in a browser:



http://127.0.0.1:8000/health



Expected result:



The API returns a healthy status and identifies the service as harvest-shield-api.



Explain that this endpoint checks whether the backend API is responding.



## 4. Demo the Field List



Open:



http://127.0.0.1:8000/api/fields



Expected result:



The API returns three sample fields:



\- TN001 - Demo Rice Field A

\- TN002 - Demo Millet Field B

\- TN003 - Demo Groundnut Field C



The response includes field metadata such as crop type, coordinates, area, and status.



Explain that the field list currently comes from the project's local JSON dataset.



## 5. Demo a Field's Crop-Health Response



Open:



http://127.0.0.1:8000/api/health/TN001



Expected result:



The response contains field information, satellite-related data, weather information, risk information, recommendations, a generation timestamp, and a disclaimer.



Important observations:



\- Satellite measurements are placeholders and may be null.

\- Weather measurements are placeholders and may be null.

\- The risk status is unknown when sufficient real observations are unavailable.

\- Recommendations are generic and must not be presented as validated agricultural advice.



Explain that the response demonstrates the intended API structure, not a verified real-time crop diagnosis.



## 6. Demo an Unknown Field



Open:



http://127.0.0.1:8000/api/health/UNKNOWN999



Expected result:



The API returns HTTP 404 because the requested field does not exist.



Explain that the backend handles unknown field IDs rather than returning a valid crop-health result for a nonexistent field.



## 7. Demo Interactive API Documentation



Open:



http://127.0.0.1:8000/docs



Expected result:



FastAPI displays its interactive API documentation.



Explain that the documentation allows a developer to inspect available endpoints, view request and response formats, and try supported API requests.



## 8. Automated Test Results



On the feature/qa-docs branch, the recorded command was:



python -m pytest -v



Recorded result: 7 tests passed, with 1 deprecation warning.



These tests cover the field and health API behavior on this branch.



The satellite-service branch was tested separately and recorded 15 passing tests with 1 deprecation warning. Those additional satellite-service tests are not part of the feature/qa-docs branch unless the changes are integrated.



These are recorded results from separate test runs. Run the command again if fresh test evidence is required.



## 9. Current Limitations



\- The field dataset contains sample records.

\- The health service returns synthetic placeholder data.

\- Live satellite imagery is not integrated into the health response.

\- Live weather data is not integrated into the health response.

\- Agricultural risk cannot be reliably assessed from the current placeholder measurements.

\- The satellite-service branch contains separate CSV-based NDVI history work; this does not by itself establish live satellite imagery processing.

\- A working Streamlit dashboard has not been verified on this branch.



## 10. Suggested Demo Closing



Harvest Shield currently demonstrates the backend API structure, sample field metadata, crop-health response format, basic error handling, and automated tests.



The next development steps are to integrate verified satellite and weather observations, connect those observations to the health service, validate risk calculations, and verify the dashboard integration.



All current crop-health outputs should be treated as demonstration data, not as confirmed agricultural assessments.


