import os
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_API_URL = "http://127.0.0.1:8000"
API_BASE_URL = os.getenv("HARVEST_SHIELD_API_URL", DEFAULT_API_URL).rstrip("/")
REQUEST_TIMEOUT = 8

st.set_page_config(
    page_title="Harvest Shield | Agricultural Intelligence",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Clearly labelled fallback data for standalone/demo deployments.
# These values are illustrative and must not be presented as live observations.
# ---------------------------------------------------------------------------
FALLBACK_FIELDS = {
    "count": 3,
    "fields": [
        {
            "field_id": "TN001",
            "field_name": "Cauvery Delta Block A",
            "crop_type": "Paddy",
            "area_hectares": 12.5,
            "metadata": "Alluvial soil, flood-prone",
        },
        {
            "field_id": "TN002",
            "field_name": "Kongu Dryland Plot 3",
            "crop_type": "Maize",
            "area_hectares": 8.0,
            "metadata": "Red soil, drip irrigation",
        },
        {
            "field_id": "TN003",
            "field_name": "Thanjavur Organic Farm",
            "crop_type": "Sugarcane",
            "area_hectares": 15.2,
            "metadata": "Heavy clay, high water retention",
        },
    ],
}

FALLBACK_HEALTH = {
    "TN001": {
        "field": FALLBACK_FIELDS["fields"][0],
        "satellite": {
            "current_ndvi": 0.72,
            "previous_ndvi": 0.68,
            "observation_date": "2026-10-15",
            "status": "synthetic",
            "source": "Illustrative sample data",
        },
        "weather": {
            "temperature_c": 31.5,
            "humidity_pct": 78.0,
            "recent_rainfall_mm": 14.2,
            "status": "synthetic",
            "source": "Illustrative sample data",
        },
        "risk": {
            "risk_level": "moderate",
            "vegetation_risk": "low",
            "weather_risk": "moderate",
            "disease_risk": "low",
            "explanations": [
                "Illustrative scenario: recent rainfall could warrant checking drainage in low-lying sections.",
                "The sample NDVI value is shown for interface demonstration only.",
            ],
        },
        "recommendations": [
            "Inspect drainage channels and check for standing water.",
            "Verify field conditions before taking crop-management action.",
        ],
    },
    "TN002": {
        "field": FALLBACK_FIELDS["fields"][1],
        "satellite": {
            "current_ndvi": 0.58,
            "previous_ndvi": 0.61,
            "observation_date": "2026-10-14",
            "status": "synthetic",
            "source": "Illustrative sample data",
        },
        "weather": {
            "temperature_c": 34.2,
            "humidity_pct": 52.0,
            "recent_rainfall_mm": 2.1,
            "status": "synthetic",
            "source": "Illustrative sample data",
        },
        "risk": {
            "risk_level": "low",
            "vegetation_risk": "low",
            "weather_risk": "low",
            "disease_risk": "low",
            "explanations": [
                "Illustrative scenario: the sample vegetation indicator has changed slightly.",
                "Confirm soil moisture with field observations; a satellite indicator alone is not a soil-moisture measurement.",
            ],
        },
        "recommendations": [
            "Continue routine monitoring.",
            "Verify irrigation needs using field observations and crop-specific guidance.",
        ],
    },
    "TN003": {
        "field": FALLBACK_FIELDS["fields"][2],
        "satellite": {
            "current_ndvi": 0.81,
            "previous_ndvi": 0.79,
            "observation_date": "2026-10-15",
            "status": "synthetic",
            "source": "Illustrative sample data",
        },
        "weather": {
            "temperature_c": 30.0,
            "humidity_pct": 82.0,
            "recent_rainfall_mm": 22.5,
            "status": "synthetic",
            "source": "Illustrative sample data",
        },
        "risk": {
            "risk_level": "high",
            "vegetation_risk": "low",
            "weather_risk": "high",
            "disease_risk": "moderate",
            "explanations": [
                "Illustrative scenario: rainfall combined with high water-retention soil may justify a drainage inspection.",
                "The sample NDVI value does not establish that the crop is disease-free.",
            ],
        },
        "recommendations": [
            "Inspect surface drainage and look for standing water.",
            "Check crop bases for visible symptoms and consult a local agricultural specialist if concerns persist.",
        ],
    },
}


# ---------------------------------------------------------------------------
# Data access and formatting
# ---------------------------------------------------------------------------
def get_json(endpoint):
    """Fetch fresh JSON and return (data, error, source_mode).

    Requests are deliberately made on each Streamlit rerun and send no-cache
    headers. The dashboard does not cache API responses in Streamlit.
    """
    url = f"{API_BASE_URL}{endpoint}"
    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={
                "Cache-Control": "no-cache, no-store, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object.")
        return data, None, "api"
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        if endpoint == "/api/fields":
            return FALLBACK_FIELDS, None, "sample"
        if endpoint.startswith("/api/health/"):
            field_id = endpoint.rsplit("/", 1)[-1]
            if field_id in FALLBACK_HEALTH:
                return FALLBACK_HEALTH[field_id], None, "sample"
        return None, "Cannot connect to the API. Check the backend URL and service status.", "unavailable"
    except requests.exceptions.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else "unknown"
        return None, f"The API returned HTTP {code}.", "error"
    except (requests.exceptions.RequestException, ValueError):
        return None, "The API response was invalid or unreadable.", "error"


def display_value(value, suffix=""):
    if value is None or isinstance(value, bool):
        return "Unavailable"
    if isinstance(value, str) and not value.strip():
        return "Unavailable"
    try:
        if pd.isna(value):
            return "Unavailable"
    except (TypeError, ValueError):
        pass
    return f"{value}{suffix}"


def safe_float(value):
    try:
        if value is None or isinstance(value, bool):
            return None
        result = float(value)
        return result if pd.notna(result) else None
    except (TypeError, ValueError):
        return None


def provenance_label(status, mode="api"):
    if mode == "sample":
        return "SIMULATED DEMO DATA"
    labels = {
        "live": "Live source (as reported by API)",
        "cached": "Cached source",
        "synthetic": "Synthetic sample",
        "sample": "Sample data",
        "unavailable": "Unavailable",
    }
    return labels.get(str(status or "").lower(), "Source not specified")


def normalize_risk(value):
    value = str(value or "unknown").strip().lower()
    if value in {"critical", "high", "moderate", "medium", "low", "normal"}:
        return value
    return "unknown"


def risk_color(value):
    return {
        "critical": "#b42318",
        "high": "#d94841",
        "moderate": "#c47b13",
        "medium": "#c47b13",
        "low": "#25855a",
        "normal": "#25855a",
        "unknown": "#64748b",
    }.get(normalize_risk(value), "#64748b")


def risk_badge(value):
    level = normalize_risk(value)
    label = level.upper() if level != "unknown" else "UNKNOWN"
    return f'<span class="risk-badge" style="--risk-color:{risk_color(level)}">{label}</span>'


def safe_list(value):
    return value if isinstance(value, list) else []


# ---------------------------------------------------------------------------
# Visual design
# ---------------------------------------------------------------------------
def inject_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');

        :root {
            --hs-forest: #123d2b;
            --hs-green: #21734b;
            --hs-mint: #e7f4eb;
            --hs-ink: #16251d;
            --hs-muted: #66756c;
            --hs-line: #e3eae5;
            --hs-card: #ffffff;
        }
        html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
        .stApp { background: #f5f8f5; color: var(--hs-ink); }
        [data-testid="stHeader"] { background: rgba(245,248,245,.92); }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #123d2b 0%, #174b35 100%);
            border-right: 0;
        }
        [data-testid="stSidebar"] * { color: #f5fff7 !important; }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] {
            background: #ffffff;
            border-radius: 10px;
        }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] * {
            color: #173c2b !important;
        }
        h1, h2, h3 { font-family: 'Manrope', sans-serif !important; letter-spacing: -.035em; }
        h1 { color: var(--hs-forest); font-weight: 800 !important; }
        h2, h3 { color: var(--hs-forest); }
        .hero {
            background: linear-gradient(120deg, #123d2b 0%, #1e6845 70%, #2e8558 100%);
            padding: 1.65rem 1.8rem; border-radius: 22px; color: #fff;
            margin-bottom: 1.15rem; box-shadow: 0 10px 28px rgba(18,61,43,.13);
            position: relative; overflow: hidden;
        }
        .hero:after {
            content: '🌾'; position: absolute; right: 2.1rem; top: 1rem;
            font-size: 5rem; opacity: .16; transform: rotate(-12deg);
        }
        .hero-kicker { text-transform: uppercase; font-size: .72rem; letter-spacing: .16em; opacity: .78; font-weight: 700; }
        .hero-title { font-family: 'Manrope', sans-serif; font-size: 2.15rem; line-height: 1.15; font-weight: 800; margin: .35rem 0 .5rem; }
        .hero-subtitle { font-size: .98rem; opacity: .88; max-width: 720px; }
        .hero-foot { margin-top: 1.1rem; display: flex; flex-wrap: wrap; gap: .5rem; }
        .hero-chip { border: 1px solid rgba(255,255,255,.28); background: rgba(255,255,255,.1); padding: .35rem .65rem; border-radius: 999px; font-size: .75rem; }
        .section-kicker { color: #718076; text-transform: uppercase; font-weight: 700; letter-spacing: .12em; font-size: .69rem; margin: .4rem 0 .2rem; }
        .section-title { font-family: 'Manrope', sans-serif; font-size: 1.35rem; font-weight: 800; color: #173e2c; margin-bottom: .7rem; }
        .metric-card {
            background: #fff; border: 1px solid var(--hs-line); border-radius: 17px;
            padding: 1rem 1.1rem; min-height: 126px; box-shadow: 0 3px 12px rgba(19,48,31,.035);
        }
        .metric-label { font-size: .78rem; font-weight: 700; color: #718076; }
        .metric-value { font-family: 'Manrope', sans-serif; font-size: 1.85rem; line-height: 1.25; font-weight: 800; color: #173e2c; margin-top: .3rem; }
        .metric-foot { color: #7a887f; font-size: .73rem; margin-top: .25rem; }
        .panel {
            background: #fff; border: 1px solid var(--hs-line); border-radius: 17px;
            padding: 1rem 1.1rem; margin-bottom: .75rem;
        }
        .field-card {
            background: #fff; border: 1px solid var(--hs-line); border-radius: 16px;
            padding: 1rem; margin-bottom: .55rem;
        }
        .field-name { font-weight: 800; color: #173e2c; font-size: 1rem; }
        .muted { color: #718076; font-size: .82rem; }
        .risk-badge {
            display: inline-block; background: color-mix(in srgb, var(--risk-color) 12%, white);
            border: 1px solid color-mix(in srgb, var(--risk-color) 30%, white);
            color: var(--risk-color); padding: .25rem .58rem; border-radius: 999px;
            font-weight: 800; letter-spacing: .04em; font-size: .68rem;
        }
        .notice {
            background: #fff8e8; border: 1px solid #f1d9a5; border-radius: 12px;
            padding: .8rem 1rem; color: #704d12; font-size: .84rem; margin: .5rem 0 1rem;
        }
        .success-note {
            background: #eaf6ee; border: 1px solid #cce7d4; border-radius: 12px;
            padding: .8rem 1rem; color: #205b39; font-size: .84rem; margin: .5rem 0 1rem;
        }
        div[data-testid="stMetric"] {
            background: #fff; border: 1px solid var(--hs-line); border-radius: 15px;
            padding: .8rem 1rem;
        }
        div[data-testid="stMetricLabel"] { color: #718076; }
        div[data-testid="stMetricValue"] { color: #173e2c; font-family: 'Manrope', sans-serif; }
        .stButton button, .stDownloadButton button {
            border-radius: 10px; font-weight: 700; border: 1px solid #d7e5da;
        }
        .stButton button[kind="primary"] { background: #1f7048; border-color: #1f7048; }
        hr { border-color: #e2eae4; }
        footer { visibility: hidden; }
        @media (max-width: 700px) {
            .hero { padding: 1.2rem; }
            .hero-title { font-size: 1.7rem; }
            .hero:after { right: .5rem; font-size: 3.4rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label, value, foot="", icon=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{icon} {label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-foot">{foot}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_heading(kicker, title):
    st.markdown(
        f'<div class="section-kicker">{kicker}</div><div class="section-title">{title}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
def main():
    inject_styles()

    # Define this before rendering the hero banner, which uses refresh_display.
    # This prevents UnboundLocalError during Streamlit's first execution.
    refresh_time = st.session_state.get("hs_last_refresh_at")
    if refresh_time:
        try:
            refresh_display = (
                datetime.fromisoformat(refresh_time)
                .astimezone()
                .strftime("%d %b %Y, %H:%M:%S")
            )
        except (TypeError, ValueError):
            refresh_display = str(refresh_time)
    else:
        refresh_display = datetime.now().astimezone().strftime(
            "%d %b %Y, %H:%M:%S"
        )

    st.sidebar.markdown(
        """
        <div style="padding:.5rem 0 1.2rem">
          <div style="font-size:2rem">🌾</div>
          <div style="font-family:Manrope,sans-serif;font-weight:800;font-size:1.25rem;line-height:1.2">HARVEST<br>SHIELD</div>
          <div style="font-size:.72rem;opacity:.75;margin-top:.5rem">AGRICULTURAL INTELLIGENCE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")
    page = st.sidebar.radio(
        "WORKSPACE",
        ["Overview", "Field intelligence", "Risk & recommendations", "Reports & data"],
        label_visibility="visible",
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("DATA CONNECTION")
    st.sidebar.code(API_BASE_URL, language=None)
    if st.sidebar.button("↻ Reload latest data", type="primary", use_container_width=True):
        st.session_state["hs_last_refresh_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        st.session_state["hs_refresh_count"] = st.session_state.get("hs_refresh_count", 0) + 1
        st.rerun()

    st.sidebar.caption("Reload requests fresh API responses. If demo data is active, the values remain illustrative until the backend is connected.")
    st.sidebar.markdown(
        '<div style="font-size:.73rem;opacity:.72;padding-top:1rem">Decision support prototype · Verify findings in the field</div>',
        unsafe_allow_html=True,
    )

    fields_response, fields_error, fields_mode = get_json("/api/fields")
    if fields_error:
        st.error(f"Unable to load fields: {fields_error}")
        st.info("Check that the FastAPI backend is running and HARVEST_SHIELD_API_URL points to the correct service.")
        st.stop()

    raw_fields = fields_response.get("fields", [])
    if not isinstance(raw_fields, list):
        st.error("The API field-list response has an invalid format.")
        st.stop()

    fields = [
        item for item in raw_fields
        if isinstance(item, dict) and isinstance(item.get("field_id"), str) and item["field_id"].strip()
    ]
    if not fields:
        st.warning("No fields are currently available. Check the data source or add fields through the existing backend.")
        st.stop()

    # Fetch each field's current health once per app run; use the same records
    # throughout the current page to keep charts and detail views consistent.
    health_by_id = {}
    health_errors = {}
    for item in fields:
        fid = item["field_id"]
        health_data, error, mode = get_json(f"/api/health/{fid}")
        if error:
            health_errors[fid] = error
        elif isinstance(health_data, dict):
            health_by_id[fid] = {"data": health_data, "mode": mode}

    summary_rows = []
    for item in fields:
        fid = item["field_id"]
        bundle = health_by_id.get(fid, {})
        data = bundle.get("data", {})
        risk = data.get("risk") if isinstance(data.get("risk"), dict) else {}
        satellite = data.get("satellite") if isinstance(data.get("satellite"), dict) else {}
        weather = data.get("weather") if isinstance(data.get("weather"), dict) else {}
        level = normalize_risk(risk.get("risk_level"))
        summary_rows.append({
            "Field ID": fid,
            "Field": item.get("field_name") or fid,
            "Crop": item.get("crop_type") or "Unspecified",
            "Area (ha)": safe_float(item.get("area_hectares")),
            "Risk": level.title() if level != "unknown" else "Unknown",
            "Risk key": level,
            "Current NDVI": safe_float(satellite.get("current_ndvi")),
            "Previous NDVI": safe_float(satellite.get("previous_ndvi")),
            "Temperature (°C)": safe_float(weather.get("temperature_c")),
            "Rainfall (mm)": safe_float(weather.get("recent_rainfall_mm")),
            "Data mode": bundle.get("mode", "unavailable"),
        })
    df = pd.DataFrame(summary_rows)
    total_area = df["Area (ha)"].sum(min_count=1)
    high_count = int(df["Risk key"].isin(["high", "critical"]).sum())
    moderate_count = int(df["Risk key"].isin(["moderate", "medium"]).sum())
    known_count = int((df["Risk key"] != "unknown").sum())
    ndvi_comparable = df.dropna(subset=["Current NDVI", "Previous NDVI"]).copy()
    ndvi_declining_count = int(
        (ndvi_comparable["Current NDVI"] < ndvi_comparable["Previous NDVI"]).sum()
    )
    total_area_text = f"{total_area:,.1f} ha" if pd.notna(total_area) else "Unavailable"
    selected_options = {
        f"{item.get('field_name') or item['field_id']} · {item['field_id']}": item["field_id"]
        for item in fields
    }
    selected_label = st.sidebar.selectbox("SELECT FIELD", list(selected_options.keys()))
    selected_id = selected_options[selected_label]
    selected_bundle = health_by_id.get(selected_id, {})
    selected_health = selected_bundle.get("data", {})
    selected_mode = selected_bundle.get("mode", "unavailable")

    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-kicker">AGRICULTURAL INTELLIGENCE · FIELD OPERATIONS</div>
          <div class="hero-title">From field signals<br>to confident next steps.</div>
          <div class="hero-subtitle">Bring field inventory, vegetation indicators, weather observations, and explainable risk screening into one operational view. Verify important signals on the ground.</div>
          <div class="hero-foot">
            <span class="hero-chip">🌱 {len(fields)} monitored fields</span>
            <span class="hero-chip">🧭 {known_count} with risk assessments</span>
            <span class="hero-chip">⏱ Data view loaded: {refresh_display}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    has_sample_data = fields_mode == "sample" or any(
        bundle.get("mode") == "sample" for bundle in health_by_id.values()
    )
    failed_health_count = len(health_errors)

    if has_sample_data:
        st.markdown(
            '<div class="notice"><b>DEMO DATA ACTIVE · NOT LIVE TELEMETRY</b><br>'
            'The dashboard could not reach the configured API for at least part of this view, so embedded illustrative data is being shown. '
            'Reloading the page will retry the API, but sample values will not change until a reachable backend returns current data.</div>',
            unsafe_allow_html=True,
        )
        if API_BASE_URL.startswith(("http://127.0.0.1", "http://localhost")):
            st.warning(
                "Deployment configuration warning: a cloud-hosted Streamlit app cannot reach a backend running on your own computer via "
                "127.0.0.1/localhost. Set HARVEST_SHIELD_API_URL to a publicly reachable, secured backend URL in the Streamlit app's Secrets/environment."
            )
    elif failed_health_count:
        st.warning(
            f"The field list loaded, but health data failed for {failed_health_count} field(s). "
            "Some charts and assessments may be incomplete."
        )
    else:
        st.markdown(
            '<div class="success-note"><b>API CONNECTED</b> · Field list and available field assessments loaded from the configured backend. '
            'Individual data sources are labelled in the field profile.</div>',
            unsafe_allow_html=True,
        )

    status_a, status_b, status_c = st.columns([1, 1, 2])
    with status_a:
        st.caption(f"**Data mode:** {'Sample / fallback' if has_sample_data else 'API response'}")
    with status_b:
        st.caption(f"**Loaded at:** {refresh_display}")
    with status_c:
        st.caption(f"**Endpoint:** `{API_BASE_URL}`")

    if page == "Overview":
        section_heading("REGIONAL PULSE", "Monitoring overview")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Fields monitored", str(len(fields)), "Fields returned by the configured API", "🌱")
        with c2:
            metric_card("Priority fields", str(high_count), "High or critical reported risk", "🚨")
        with c3:
            metric_card("NDVI trending down", str(ndvi_declining_count), "Comparable current vs previous readings", "🛰️")
        with c4:
            metric_card("Area represented", total_area_text, "Sum of available field areas", "🗺️")

        st.write("")
        left, right = st.columns([1.2, 1])
        with left:
            section_heading("RISK LANDSCAPE", "Risk distribution")
            risk_order = ["Critical", "High", "Moderate", "Medium", "Low", "Normal", "Unknown"]
            risk_counts = df["Risk"].value_counts()
            risk_counts = risk_counts.reindex([x for x in risk_order if x in risk_counts.index])
            if not risk_counts.empty:
                st.bar_chart(risk_counts, color="#2c8052", height=270)
                st.caption("Counts reflect classifications returned by the API; they are not independently validated predictions.")
            else:
                st.info("No risk classifications are available yet.")
        with right:
            section_heading("FIELD WATCHLIST", "Fields to review")
            priority_df = df[df["Risk key"].isin(["critical", "high", "moderate", "medium"])]
            if priority_df.empty:
                st.markdown('<div class="panel">No fields are currently classified as high or moderate risk by the available assessments.</div>', unsafe_allow_html=True)
            else:
                for _, row in priority_df.sort_values(
                    "Risk key", key=lambda col: col.map({"critical": 0, "high": 1, "moderate": 2, "medium": 3})
                ).iterrows():
                    st.markdown(
                        f"""
                        <div class="field-card">
                          <div style="display:flex;justify-content:space-between;gap:.5rem;align-items:center">
                            <div class="field-name">{row['Field']}</div>{risk_badge(row['Risk key'])}
                          </div>
                          <div class="muted" style="margin-top:.3rem">{row['Field ID']} · {row['Crop']} · {display_value(row['Area (ha)'], ' ha' if pd.notna(row['Area (ha)']) else '')}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            st.caption("Risk labels are screening signals. Confirm field conditions before making management decisions.")
        if has_sample_data:
            st.info(
                "Why values may not change after reload: the app is currently showing its built-in sample dataset. "
                "A refresh retries the backend connection; it does not generate new observations. "
                "To see changing/live values, connect the deployed app to the running backend and its data sources."
            )

        st.write("")
        section_heading("FIELD REGISTER", "All monitored fields")
        display_df = df[["Field ID", "Field", "Crop", "Area (ha)", "Risk", "Current NDVI", "Temperature (°C)", "Rainfall (mm)"]].copy()
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.caption("Unavailable measurements remain blank rather than being treated as zero.")

    elif page == "Field intelligence":
        section_heading("FIELD PROFILE", "Investigate a field")
        if selected_id in health_errors:
            st.error(f"Unable to load health details for {selected_id}: {health_errors[selected_id]}")
            st.stop()
        if not selected_health:
            st.warning("No health assessment is available for the selected field.")
            st.stop()

        field = selected_health.get("field") if isinstance(selected_health.get("field"), dict) else {}
        satellite = selected_health.get("satellite") if isinstance(selected_health.get("satellite"), dict) else {}
        weather = selected_health.get("weather") if isinstance(selected_health.get("weather"), dict) else {}
        risk = selected_health.get("risk") if isinstance(selected_health.get("risk"), dict) else {}
        level = normalize_risk(risk.get("risk_level"))

        st.markdown(
            f"""
            <div class="panel">
              <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;flex-wrap:wrap">
                <div><div class="section-kicker">SELECTED FIELD · {selected_id}</div>
                <div style="font-family:Manrope,sans-serif;font-size:1.65rem;font-weight:800;color:#173e2c">{field.get('field_name') or selected_id}</div>
                <div class="muted">{display_value(field.get('crop_type'))} · {display_value(field.get('area_hectares'), ' hectares' if field.get('area_hectares') is not None else '')}</div></div>
                <div>{risk_badge(level)}</div>
              </div>
              <div class="muted" style="margin-top:.7rem">{display_value(field.get('metadata'))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        a, b, c = st.columns(3)
        with a:
            metric_card("Current NDVI", display_value(satellite.get("current_ndvi")), "Vegetation index, if supplied", "🛰️")
        with b:
            metric_card("Temperature", display_value(weather.get("temperature_c"), " °C" if weather.get("temperature_c") is not None else ""), "Reported weather observation", "🌡️")
        with c:
            metric_card("Recent rainfall", display_value(weather.get("recent_rainfall_mm"), " mm" if weather.get("recent_rainfall_mm") is not None else ""), "Period depends on source", "🌧️")

        st.write("")
        left, right = st.columns(2)
        with left:
            section_heading("VEGETATION", "Indicator comparison")
            current_ndvi = safe_float(satellite.get("current_ndvi"))
            previous_ndvi = safe_float(satellite.get("previous_ndvi"))
            if current_ndvi is not None or previous_ndvi is not None:
                vegetation_df = pd.DataFrame(
                    {"Observation": ["Previous", "Current"], "NDVI": [previous_ndvi, current_ndvi]}
                ).set_index("Observation")
                st.bar_chart(vegetation_df, color="#2c8052", height=230)
                st.caption(f"Observation date: {display_value(satellite.get('observation_date'))}")
            else:
                st.info("No vegetation-index observations are available for this field.")
            st.caption(f"Source: {display_value(satellite.get('source'))} · {provenance_label(satellite.get('status'), selected_mode)}")
        with right:
            section_heading("LOCAL CONDITIONS", "Weather observations")
            weather_values = {
                "Temperature (°C)": safe_float(weather.get("temperature_c")),
                "Humidity (%)": safe_float(weather.get("humidity_pct")),
                "Recent rainfall (mm)": safe_float(weather.get("recent_rainfall_mm")),
            }
            weather_df = pd.DataFrame(
                [{"Measurement": k, "Value": v} for k, v in weather_values.items() if v is not None]
            )
            if not weather_df.empty:
                st.dataframe(weather_df, use_container_width=True, hide_index=True)
            else:
                st.info("No weather measurements are available for this field.")
            st.caption(f"Source: {display_value(weather.get('source'))} · {provenance_label(weather.get('status'), selected_mode)}")

        st.write("")
        section_heading("ASSESSMENT BREAKDOWN", "What is contributing to this assessment?")
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown('<div class="panel"><div class="muted">Vegetation risk</div><div style="margin-top:.45rem">' + risk_badge(risk.get("vegetation_risk")) + '</div></div>', unsafe_allow_html=True)
        with r2:
            st.markdown('<div class="panel"><div class="muted">Weather risk</div><div style="margin-top:.45rem">' + risk_badge(risk.get("weather_risk")) + '</div></div>', unsafe_allow_html=True)
        with r3:
            st.markdown('<div class="panel"><div class="muted">Disease risk</div><div style="margin-top:.45rem">' + risk_badge(risk.get("disease_risk")) + '</div></div>', unsafe_allow_html=True)

        explanations = safe_list(risk.get("explanations"))
        if explanations:
            for explanation in explanations:
                st.markdown(f"- {explanation}")
        else:
            st.info("The API has not supplied explanatory notes for this assessment.")

        st.markdown(
            '<div class="notice"><b>Interpretation note:</b> These indicators support preliminary screening. They do not independently confirm crop disease, establish causation, or replace field inspection and qualified agricultural advice.</div>',
            unsafe_allow_html=True,
        )

    elif page == "Risk & recommendations":
        section_heading("DECISION SUPPORT", "Alerts & recommended follow-up")
        filter_col, crop_col = st.columns([1, 1])
        with filter_col:
            risk_filter = st.multiselect(
                "Filter by risk level",
                options=["Critical", "High", "Moderate", "Medium", "Low", "Normal", "Unknown"],
                default=["Critical", "High", "Moderate", "Medium"],
            )
        with crop_col:
            crops = sorted(df["Crop"].dropna().astype(str).unique().tolist())
            crop_filter = st.multiselect("Filter by crop", options=crops, default=crops)

        filtered = df[df["Risk"].isin(risk_filter) & df["Crop"].isin(crop_filter)]
        if filtered.empty:
            st.info("No fields match the selected filters.")
        else:
            for _, row in filtered.iterrows():
                fid = row["Field ID"]
                bundle = health_by_id.get(fid, {})
                health = bundle.get("data", {})
                risk = health.get("risk") if isinstance(health.get("risk"), dict) else {}
                recommendations = safe_list(health.get("recommendations"))
                with st.expander(f"{row['Field']} · {fid} · {row['Risk']} risk", expanded=row["Risk key"] in {"critical", "high"}):
                    st.markdown(f"**Crop:** {row['Crop']}  |  **Area:** {display_value(row['Area (ha)'], ' ha' if pd.notna(row['Area (ha)']) else '')}")
                    st.markdown("**Assessment explanation**")
                    explanations = safe_list(risk.get("explanations"))
                    if explanations:
                        for explanation in explanations:
                            st.markdown(f"- {explanation}")
                    else:
                        st.write("No explanation supplied by the current API response.")
                    st.markdown("**Suggested follow-up**")
                    if recommendations:
                        for recommendation in recommendations:
                            st.markdown(f"- {recommendation}")
                    else:
                        st.write("No recommendation supplied. Review the field manually.")
                    st.caption("Recommendations are decision-support suggestions and should be verified against field conditions.")
        st.write("")
        st.markdown(
            '<div class="panel"><b>Action tracking status</b><br><span class="muted">This view currently displays recommendations returned by the API. Acknowledgement and persistent inspection logging are not enabled unless supported by the connected backend.</span></div>',
            unsafe_allow_html=True,
        )

    else:  # Reports & data
        section_heading("DATA EXPORT", "Reports & provenance")
        st.markdown(
            '<div class="panel"><b>Export the current fleet summary</b><br><span class="muted">Download field-level values returned by the configured API or clearly labelled embedded demo data.</span></div>',
            unsafe_allow_html=True,
        )
        export_columns = [
            "Field ID", "Field", "Crop", "Area (ha)", "Risk",
            "Current NDVI", "Previous NDVI", "Temperature (°C)", "Rainfall (mm)", "Data mode",
        ]
        export_df = df[export_columns].copy()
        export_df["Report generated at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇ Download fleet report (CSV)",
            data=csv_bytes,
            file_name=f"harvest_shield_fleet_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=False,
            type="primary",
        )
        st.write("")
        section_heading("DATA QUALITY", "What this dashboard knows")
        st.markdown(
            """
            - **Field inventory:** Based on the configured API response.
            - **Risk classifications:** Displayed from the existing application response; this dashboard does not independently validate the underlying thresholds.
            - **Satellite indicators:** May be synthetic or unavailable. Check the source and status displayed in Field Intelligence.
            - **Weather observations:** Shown as reported by the API. This dashboard does not generate forecasts.
            - **Disease assessment:** A risk label is not a confirmed diagnosis.
            """
        )
        st.dataframe(export_df, use_container_width=True, hide_index=True)
        if health_errors:
            st.warning("Some field health requests failed:")
            for failed_id, message in health_errors.items():
                st.write(f"- **{failed_id}:** {message}")

    st.divider()
    st.caption(
        "HARVEST SHIELD · Agricultural decision-support prototype · "
        "Verify important findings through field observation and appropriate agricultural expertise."
    )


if __name__ == "__main__":
    main()
