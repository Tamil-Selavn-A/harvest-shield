
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
    """Fetch JSON from the Harvest Shield API."""
    url = f"{API_BASE_URL}{endpoint}"

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict):
            raise ValueError("The API response must be a JSON object.")

        return data, None

    except requests.exceptions.Timeout:
        return None, "The API request timed out. Please try again."

    except requests.exceptions.ConnectionError:
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

    st.header(field.get("field_name") or selected_id)
    st.caption(f"Field ID: {selected_id}")

    overview = st.columns(3)
    overview[0].metric(
        "Crop type",
        display_value(field.get("crop_type")),
    )
    overview[1].metric(
        "Field area",
        display_value(field.get("area_hectares"), " hectares"),
    )
    overview[2].metric(
        "Field metadata",
        display_data_status(field.get("data_status")),
    )

    st.subheader("Overall risk assessment")

    overall_risk = risk.get("overall_risk", "unknown")
    if not isinstance(overall_risk, str) or not overall_risk.strip():
        overall_risk = "unknown"

    overall_risk = overall_risk.lower()

    if overall_risk not in {"low", "moderate", "high", "critical", "unknown"}:
        overall_risk = "unknown"

    if overall_risk == "unknown":
        st.warning(
            "Risk assessment unavailable. Do not interpret this as low risk."
        )
    else:
        st.info(f"Reported risk level: {overall_risk.title()}")

    risk_columns = st.columns(3)
    risk_columns[0].metric(
        "Vegetation risk",
        display_value(risk.get("ndvi_risk")),
    )
    risk_columns[1].metric(
        "Weather risk",
        display_value(risk.get("weather_risk")),
    )
    risk_columns[2].metric(
        "Disease risk",
        display_value(risk.get("disease_risk")),
    )

    st.subheader("Vegetation indicators")

    satellite_columns = st.columns(3)
    satellite_columns[0].metric(
        "Current NDVI",
        display_value(satellite.get("ndvi_current")),
    )
    satellite_columns[1].metric(
        "Previous NDVI",
        display_value(satellite.get("ndvi_previous")),
    )
    satellite_columns[2].metric(
        "Observation date",
        display_value(satellite.get("observation_date")),
    )

    st.caption(
        "Satellite source: "
        f"{display_value(satellite.get('data_source'))} · "
        f"Status: {display_data_status(satellite.get('data_status'))}"
    )

    if satellite.get("ndvi_current") is None:
        st.info(
            "No current NDVI measurement is available. "
            "No vegetation-health chart is shown."
        )

    st.subheader("Weather observations")

    weather_columns = st.columns(3)
    weather_columns[0].metric(
        "Temperature",
        display_value(weather.get("temperature_c"), " °C"),
    )
    weather_columns[1].metric(
        "Humidity",
        display_value(weather.get("humidity_pct"), " %"),
    )
    weather_columns[2].metric(
        "Recent rainfall",
        display_value(weather.get("recent_rainfall_mm"), " mm"),
    )

    st.caption(
        "Weather source: "
        f"{display_value(weather.get('data_source'))} · "
        f"Status: {display_data_status(weather.get('data_status'))}"
    )

    weather_message = weather.get("message")
    if isinstance(weather_message, str) and weather_message.strip():
        if weather.get("data_status") == "unavailable":
            st.warning(f"Weather data unavailable: {weather_message}")
        else:
            st.info(weather_message)

    st.subheader("Why this assessment?")
    explanations = risk.get("explanation")

    if isinstance(explanations, list) and explanations:
        for explanation in explanations:
            if isinstance(explanation, str) and explanation.strip():
                st.write(f"- {explanation}")
    else:
        st.write("No risk explanation was provided by the API.")

    st.subheader("Recommended actions")

    if recommendations:
        for index, recommendation in enumerate(recommendations, start=1):
            if not isinstance(recommendation, dict):
                continue

            action = recommendation.get("action") or "Action unspecified"
            priority = recommendation.get("priority") or "unspecified"
            reason = recommendation.get("reason") or "Reason unavailable"

            with st.expander(
                f"{index}. {action} — Priority: {priority}",
                expanded=True,
            ):
                st.write(reason)

                triggers = recommendation.get("triggers")
                if isinstance(triggers, list) and triggers:
                    st.caption("Triggers: " + ", ".join(map(str, triggers)))
    else:
        st.info("No recommendations were provided by the API.")

    st.subheader("Data provenance")
    st.write(
        f"Health response generated: "
        f"{display_value(health.get('generated_at'))}"
    )
    st.caption(
        "This dashboard displays information supplied by the backend. "
        "Synthetic and sample data are not verified live observations."
    )

    st.warning(
        health.get("disclaimer")
        or (
            "Use this dashboard as decision support, not as a substitute "
            "for field inspection or professional agricultural advice."
        )
    )


if __name__ == "__main__":
    main()
