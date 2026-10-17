import os

import requests
import streamlit as st


DEFAULT_API_URL = "http://127.0.0.1:8000"
API_BASE_URL = os.getenv(
    "HARVEST_SHIELD_API_URL",
    DEFAULT_API_URL,
).rstrip("/")

REQUEST_TIMEOUT = 8


st.set_page_config(
    page_title="Harvest Shield | Field Monitor",
    page_icon="🌱",
    layout="wide",
)


def get_json(endpoint):
    """Fetch JSON from the Harvest Shield API, with local fallback for cloud deployments."""
    url = f"{API_BASE_URL}{endpoint}"

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict):
            raise ValueError("The API response must be a JSON object.")

        return data, None

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # Fallback for Streamlit Cloud where localhost backend isn't running
        try:
            if endpoint == "/api/fields":
                from backend.services.field_service import get_all_fields
                fields = get_all_fields()
                return {"count": len(fields), "fields": fields}, None
            elif endpoint.startswith("/api/health/"):
                field_id = endpoint.split("/")[-1]
                from backend.services.health_service import get_crop_health
                health_data = get_crop_health(field_id)
                return health_data, None
        except Exception:
            pass

        return None, (
            "Cannot connect to the Harvest Shield API. "
            "Check that the backend is running."
        )

    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response else "unknown"
        return None, f"The API returned HTTP {status_code}."

    except (requests.exceptions.RequestException, ValueError):
        return None, "The API returned an invalid or unreadable response."


def display_value(value, suffix=""):
    """Render missing values honestly instead of treating them as zero."""
    if value is None or isinstance(value, bool):
        return "Unavailable"

    if isinstance(value, str) and not value.strip():
        return "Unavailable"

    return f"{value}{suffix}"


def display_data_status(status):
    """Convert API provenance into a readable label."""
    labels = {
        "live": "Live",
        "cached": "Cached",
        "synthetic": "Synthetic sample",
        "unavailable": "Unavailable",
        "sample": "Sample metadata",
    }

    if not isinstance(status, str):
        return "Unspecified"

    return labels.get(status.lower(), "Unspecified")


def main():
    st.title("🌱 Harvest Shield")
    st.caption(
        "Crop-health monitoring and field inspection support. "
        "Review field information, available observations, and risk explanations."
    )

    st.sidebar.header("Field selection")
    st.sidebar.caption(f"API: {API_BASE_URL}")

    if st.sidebar.button("Refresh data", use_container_width=True):
        st.rerun()

    fields_response, fields_error = get_json("/api/fields")

    if fields_error:
        st.error(f"Unable to load fields: {fields_error}")
        st.info(
            "Start the FastAPI backend and refresh this page to try again."
        )
        st.stop()

    fields = fields_response.get("fields")

    if not isinstance(fields, list):
        st.error("The API field-list response has an invalid format.")
        st.stop()

    valid_fields = [
        field
        for field in fields
        if isinstance(field, dict)
        and isinstance(field.get("field_id"), str)
        and field["field_id"].strip()
    ]

    if not valid_fields:
        st.warning("No fields are currently available from the API.")
        st.stop()

    field_options = {
        f"{field.get('field_name') or field['field_id']} "
        f"({field['field_id']})": field["field_id"]
        for field in valid_fields
    }

    selected_label = st.sidebar.selectbox(
        "Choose a field",
        options=list(field_options.keys()),
    )
    selected_id = field_options[selected_label]

    health, health_error = get_json(f"/api/health/{selected_id}")

    if health_error:
        st.error(f"Unable to load crop health: {health_error}")
        st.stop()

    field = health.get("field")
    satellite = health.get("satellite")
    weather = health.get("weather")
    risk = health.get("risk")
    recommendations = health.get("recommendations")

    if not isinstance(field, dict):
        st.error("The health response does not contain valid field details.")
        st.stop()

    if not isinstance(satellite, dict):
        satellite = {}

    if not isinstance(weather, dict):
        weather = {}

    if not isinstance(risk, dict):
        risk = {}

    if not isinstance(recommendations, list):
        recommendations = []

    st.header(field.get("field_name", selected_id))
    st.caption(f"Field ID: {selected_id}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Crop type", display_value(field.get("crop_type")))
    with col2:
        area = field.get("area_hectares")
        st.metric("Field area", display_value(area, " hectares" if area is not None else ""))
    with col3:
        st.metric("Field metadata", display_value(field.get("metadata")))

    st.subheader("Overall risk assessment")
    risk_level = risk.get("risk_level", "unknown")
    st.info(f"Reported risk level: {risk_level.capitalize()}")

    rcol1, rcol2, rcol3 = st.columns(3)
    with rcol1:
        st.metric("Vegetation risk", display_value(risk.get("vegetation_risk")))
    with rcol2:
        st.metric("Weather risk", display_value(risk.get("weather_risk")))
    with rcol3:
        st.metric("Disease risk", display_value(risk.get("disease_risk")))

    st.subheader("Vegetation indicators")
    vcol1, vcol2, vcol3 = st.columns(3)
    with vcol1:
        st.metric("Current NDVI", display_value(satellite.get("current_ndvi")))
    with vcol2:
        st.metric("Previous NDVI", display_value(satellite.get("previous_ndvi")))
    with vcol3:
        st.metric("Observation date", display_value(satellite.get("observation_date")))

    sat_status = display_data_status(satellite.get("status"))
    sat_source = satellite.get("source", "unavailable")
    st.caption(f"Satellite source: {sat_source} • Status: {sat_status}")

    st.subheader("Weather observations")
    wcol1, wcol2, wcol3 = st.columns(3)
    with wcol1:
        temp = weather.get("temperature_c")
        st.metric("Temperature", display_value(temp, " °C" if temp is not None else ""))
    with wcol2:
        humidity = weather.get("humidity_pct")
        st.metric("Humidity", display_value(humidity, " %" if humidity is not None else ""))
    with wcol3:
        rain = weather.get("recent_rainfall_mm")
        st.metric("Recent rainfall", display_value(rain, " mm" if rain is not None else ""))

    weather_status = display_data_status(weather.get("status"))
    weather_source = weather.get("source", "unavailable")
    st.caption(f"Weather source: {weather_source} • Status: {weather_status}")

    st.subheader("Why this assessment?")
    explanations = risk.get("explanations", [])
    if explanations:
        for exp in explanations:
            st.markdown(f"* {exp}")
    else:
        st.info("No explanatory notes available.")

    st.subheader("Recommended actions")
    if recommendations:
        for rec in recommendations:
            st.markdown(f"* {rec}")
    else:
        st.info("No recommended actions at this time.")


if __name__ == "__main__":
    main()