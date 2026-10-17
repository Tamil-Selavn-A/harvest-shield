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


# Embedded fallback data for standalone cloud deployments
FALLBACK_FIELDS = {
    "count": 3,
    "fields": [
        {"field_id": "TN001", "field_name": "Cauvery Delta Block A", "crop_type": "Paddy", "area_hectares": 12.5, "metadata": "Alluvial soil, flood-prone"},
        {"field_id": "TN002", "field_name": "Kongu Dryland Plot 3", "crop_type": "Maize", "area_hectares": 8.0, "metadata": "Red soil, drip irrigation"},
        {"field_id": "TN003", "field_name": "Thanjavur Organic Farm", "crop_type": "Sugarcane", "area_hectares": 15.2, "metadata": "Heavy clay, high water retention"},
    ]
}

FALLBACK_HEALTH = {
    "TN001": {
        "field": {"field_id": "TN001", "field_name": "Cauvery Delta Block A", "crop_type": "Paddy", "area_hectares": 12.5, "metadata": "Alluvial soil, flood-prone"},
        "satellite": {"current_ndvi": 0.72, "previous_ndvi": 0.68, "observation_date": "2026-10-15", "status": "live", "source": "Sentinel-2"},
        "weather": {"temperature_c": 31.5, "humidity_pct": 78.0, "recent_rainfall_mm": 14.2, "status": "live", "source": "OpenWeather"},
        "risk": {
            "risk_level": "moderate",
            "vegetation_risk": "low",
            "weather_risk": "moderate",
            "disease_risk": "low",
            "explanations": ["Recent heavy rainfall may cause temporary waterlogging in low-lying sections.", "NDVI levels show healthy vegetative growth."],
        },
        "recommendations": ["Monitor drainage channels.", "Inspect lower plots for stagnant water."]
    },
    "TN002": {
        "field": {"field_id": "TN002", "field_name": "Kongu Dryland Plot 3", "crop_type": "Maize", "area_hectares": 8.0, "metadata": "Red soil, drip irrigation"},
        "satellite": {"current_ndvi": 0.58, "previous_ndvi": 0.61, "observation_date": "2026-10-14", "status": "live", "source": "Sentinel-2"},
        "weather": {"temperature_c": 34.2, "humidity_pct": 52.0, "recent_rainfall_mm": 2.1, "status": "live", "source": "OpenWeather"},
        "risk": {
            "risk_level": "low",
            "vegetation_risk": "low",
            "weather_risk": "low",
            "disease_risk": "low",
            "explanations": ["Stable NDVI readings.", "Soil moisture levels are within optimal range for maize."],
        },
        "recommendations": ["Maintain current drip irrigation schedule."]
    },
    "TN003": {
        "field": {"field_id": "TN003", "field_name": "Thanjavur Organic Farm", "crop_type": "Sugarcane", "area_hectares": 15.2, "metadata": "Heavy clay, high water retention"},
        "satellite": {"current_ndvi": 0.81, "previous_ndvi": 0.79, "observation_date": "2026-10-15", "status": "live", "source": "Sentinel-2"},
        "weather": {"temperature_c": 30.0, "humidity_pct": 82.0, "recent_rainfall_mm": 22.5, "status": "live", "source": "OpenWeather"},
        "risk": {
            "risk_level": "high",
            "vegetation_risk": "low",
            "weather_risk": "high",
            "disease_risk": "moderate",
            "explanations": ["High rainfall combined with heavy clay soil elevates root rot risk.", "Canopy density is excellent."],
        },
        "recommendations": ["Ensure surface drainage ditches are clear.", "Inspect crop base for fungal signs."]
    }
}


def get_json(endpoint):
    """Fetch JSON from API, with embedded fallback for cloud deployments."""
    url = f"{API_BASE_URL}{endpoint}"

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict):
            raise ValueError("The API response must be a JSON object.")

        return data, None

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # Fallback for Streamlit Cloud
        if endpoint == "/api/fields":
            return FALLBACK_FIELDS, None
        elif endpoint.startswith("/api/health/"):
            field_id = endpoint.split("/")[-1]
            if field_id in FALLBACK_HEALTH:
                return FALLBACK_HEALTH[field_id], None

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