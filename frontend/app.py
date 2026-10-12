import streamlit as st
import requests
from PIL import Image
import io
import logging
import math
import mimetypes
import os
from pathlib import Path

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080").rstrip("/")
REQUEST_TIMEOUT_SECONDS = (5, 60)
MAX_UPLOAD_BYTES = 10_000_000
SAMPLE_DIRECTORY = Path(__file__).resolve().parents[1] / "data_samples"
MODE_LOCATION = "Satellite location"
MODE_UPLOAD = "Upload image"
MIN_SEARCH_CHARACTERS = 3
SEARCH_DEBOUNCE_MS = 350
SUGGEST_TIMEOUT_SECONDS = (3, 10)
MAP_CLICK_FALLBACK_LABEL = "Chosen from the map"
# Both typeaheads are reset together so they always show the same place.
SEARCHBOX_KEYS = ("place_search_sidebar", "place_search_map")
IMAGERY_UNAVAILABLE_MESSAGE = "Satellite imagery could not be loaded; the analysis remains valid."
GOOGLE_MAPS_SOURCE_LABEL = "Imagery source: Google Maps"
JPEG_MIME_TYPE = "image/jpeg"

# Verified against the deployed backend on 2026-10-04. The first entry is the demo
# opener and scores CRITICAL; Botanic Gardens is the low-risk contrast.
CITY_COORDINATES = {
    "Singapore Port Terminal": (1.2897, 103.7540),
    "Singapore Urban Core": (1.3343, 103.8563),
    "Singapore Botanic Gardens": (1.3521, 103.8198),
    "Bangkok City Centre": (13.7563, 100.5018),
    "Delhi Karol Bagh": (28.6450, 77.2200),
}
RISK_COLORS = {"LOW": "green", "MODERATE": "green", "HIGH": "orange", "CRITICAL": "red"}# Hex rather than named colours: st.map needs explicit values per point.
MAP_RISK_COLOURS = {"CRITICAL": "#ff4d4f", "HIGH": "#ff9f43", "MODERATE": "#ffd166", "LOW": "#2dd4a7"}
MATERIALS = [
    ("Asphalt", "asphalt_pct", "#555555"),
    ("Dark Roofs", "dark_roof_pct", "#181818"),
    ("Concrete", "concrete_pct", "#c9cdd1"),
    ("Green Canopy", "green_canopy_pct", "#43b879"),
]
logger = logging.getLogger(__name__)


def display_value(value, suffix=""):
    return "-" if value is None else f"{value}{suffix}"


def render_critical_alert(report):
    if report.get("risk_level") == "CRITICAL":
        if report.get("alert_dispatched") is True:
            st.error("CRITICAL HEAT RISK: Automated Pub/Sub alert dispatched. Published successfully.")
        elif report.get("alert_attempted") is True:
            st.warning("CRITICAL HEAT RISK: Pub/Sub alert dispatch not confirmed. Publication attempted and failed; notify the response team.")
        elif report.get("alert_attempted") is False:
            st.warning("CRITICAL HEAT RISK: Pub/Sub alert dispatch not confirmed. Publication not attempted; notify the response team.")
        else:
            st.warning("CRITICAL HEAT RISK: Pub/Sub alert dispatch not confirmed. Attempt status unavailable for this report.")


@st.cache_data(max_entries=12, show_spinner=False)
def load_preset(path, modified_at):
    return Path(path).read_bytes()


def render_response_error(response, context):
    logger.warning("%s request failed: HTTP %s", context, response.status_code)
    message = "Please try again shortly."
    code = ""
    try:
        envelope = response.json()
        if isinstance(envelope, dict) and isinstance(envelope.get("code"), str) and isinstance(envelope.get("message"), str):
            message = envelope["message"]
            code = f" [{envelope['code']}]"
    except (ValueError, requests.RequestException):
        pass
    st.error(f"{context} unavailable (HTTP {response.status_code}){code}. {message}")


def render_request_error(error, context):
    logger.warning("%s failed: %s", context, type(error).__name__)
    if isinstance(error, requests.Timeout):
        st.error(f"{context} timed out. Check that the backend is running, then try again.")
    elif isinstance(error, requests.ConnectionError):
        st.error("Backend unavailable. Start it with `uvicorn main:app --port 8080` from the backend directory, then try again.")
    else:
        st.error(f"{context} could not be completed. Please retry or ask a developer to check the server logs.")


def surface_values(surfaces):
    return [
        ("Asphalt", surfaces.get("asphalt_pct")),
        ("Dark Roofs", surfaces.get("dark_roof_pct")),
        ("Concrete", surfaces.get("concrete_pct")),
        ("Green Canopy", surfaces.get("green_canopy_pct")),
    ]


def render_surface_chart(surfaces):
    values = [
        {"Material": label, "Coverage": percentage}
        for label, percentage in surface_values(surfaces)
        if percentage is not None
    ]
    if not values:
        st.info("Surface breakdown unavailable for this report.")
        return
    st.vega_lite_chart(
        spec={
            "data": {"values": values},
            "height": 190,
            "mark": {"type": "bar", "stroke": "#888888", "strokeWidth": 1},
            "encoding": {
                "y": {"field": "Material", "type": "nominal", "sort": [item[0] for item in MATERIALS], "title": None},
                "x": {"field": "Coverage", "type": "quantitative", "scale": {"domain": [0, 100]}, "title": "Surface coverage (%)"},
                "color": {
                    "field": "Material", "type": "nominal", "legend": None,
                    "scale": {"domain": [item[0] for item in MATERIALS], "range": [item[2] for item in MATERIALS]},
                },
                "tooltip": [{"field": "Material"}, {"field": "Coverage", "type": "quantitative", "title": "Coverage (%)"}],
            },
        },
        width="stretch",
    )


def render_score(data):
    risk = data.get("risk_level")
    with st.container(horizontal=True, vertical_alignment="center"):
        if risk in RISK_COLORS:
            st.badge(risk, color=RISK_COLORS[risk])
        else:
            st.caption("Risk level: -")
        st.subheader(display_value(data.get("zone_name")))
    plan = data.get("passive_cooling_plan") or {}
    # Bordered cards so the headline numbers stay legible when projected.
    metrics = st.columns(3, border=True)
    metrics[0].metric("HVI (1-10)", display_value(data.get("hvi_score")))
    metrics[1].metric("Ambient Temp", display_value(data.get("ambient_temp_c"), " °C"))
    metrics[2].metric("Projected Cooling Drop", display_value(plan.get("projected_surface_temp_drop_c"), " °C"))
    provenance = {"bigquery": "BigQuery / NOAA GSOD", "fallback": "Offline fallback", "caller": "Analyst what-if input"}
    st.caption(f"Temperature source: {provenance.get(data.get('climate_source'), '-')}")
    if data.get("climate_source") == "bigquery":
        st.success("MEASURED TELEMETRY · BigQuery / NOAA GSOD", icon=":material/verified:")
    elif data.get("climate_source") == "fallback":
        st.info("Live climate telemetry unavailable. This report uses the backend's fallback temperature.")
    elif data.get("climate_source") == "caller":
        st.warning("WHAT-IF · Analyst-supplied temperature. Not measured telemetry.")


def render_image_source(report):
    source = report.get("image_source")
    if source == "caller":
        st.info("CALLER IMAGE · Analyst-provided imagery")
    elif source == "google_maps":
        st.success("SATELLITE IMAGERY · Retrieved by the backend for this location")
    else:
        st.caption("Image source: -")


def render_satellite_imagery_unavailable(satellite_preview, report):
    with satellite_preview.container():
        if report.get("attribution_required") is True:
            st.error("Required Google Maps attribution image is unavailable. This report is not presented as attribution-compliant.")
        else:
            st.info(IMAGERY_UNAVAILABLE_MESSAGE)


def apply_location_preset():
    location = st.session_state.get("location_preset")
    if location in CITY_COORDINATES:
        latitude, longitude = CITY_COORDINATES[location]
        st.session_state["imagery_latitude"] = str(latitude)
        st.session_state["imagery_longitude"] = str(longitude)
        st.session_state["resolved_place"] = location


def render_blueprint(report):
    st.divider()
    surfaces_column, plan_column = st.columns([1, 1])
    surfaces = report.get("surface_breakdown") or {}
    # Each half is its own bordered card so the diagnosis and the prescription
    # read as two distinct things rather than one continuous wall of numbers.
    with surfaces_column, st.container(border=True):
        st.subheader("Surface material breakdown", divider="grey")
        render_surface_chart(surfaces)
        with st.container(horizontal=True):
            for label, percentage in surface_values(surfaces):
                st.metric(label, display_value(percentage, "%"))
    with plan_column, st.container(border=True):
        st.subheader("Passive cooling blueprint", divider="grey")
        plan = report.get("passive_cooling_plan") or {}
        if not plan:
            st.info("Passive cooling plan unavailable for this report.")
        st.markdown("**Wind corridor orientation**")
        st.text(display_value(plan.get("corridor_orientation")))
        with st.container(horizontal=True):
            st.metric("Retroreflective coating area", display_value(plan.get("retroreflective_coating_sqm"), " m²"), border=True)
            st.metric("Projected temperature drop", display_value(plan.get("projected_surface_temp_drop_c"), " °C"), border=True)
        st.markdown("**Micro-canopy interventions**")
        interventions = plan.get("micro_canopy_interventions") or []
        if not interventions:
            st.info("Micro-canopy interventions unavailable for this report.")
        for index, intervention in enumerate(interventions):
            if intervention is not None:
                st.checkbox(str(intervention), key=f"intervention_{report.get('zone_id')}_{index}")


def set_coordinates(latitude, longitude, label=None):
    """Single place where any of the three input methods lands a coordinate."""
    st.session_state["imagery_latitude"] = f"{float(latitude):.6f}"
    st.session_state["imagery_longitude"] = f"{float(longitude):.6f}"
    # Any explicit choice means the preset no longer describes the coordinates.
    st.session_state["location_preset"] = "Custom coordinates"
    st.session_state["resolved_place"] = label


def fetch_place_suggestions(searchterm):
    """Typeahead source. Runs per keystroke, so it must never raise."""
    query = (searchterm or "").strip()
    if len(query) < MIN_SEARCH_CHARACTERS:
        return []
    try:
        response = requests.get(f"{API_BASE_URL}/api/places/suggest",
                                params={"q": query}, timeout=SUGGEST_TIMEOUT_SECONDS)
        if response.status_code != 200:
            return []
        suggestions = response.json().get("suggestions") or []
    except Exception:
        # A failed suggestion is not worth interrupting typing over.
        return []
    return [(item["description"], (item["description"], item["place_id"])) for item in suggestions
            if item.get("description") and item.get("place_id")]


def select_place(chosen):
    """Resolve a chosen suggestion by place_id, which is exact where a name is not."""
    description, place_id = chosen
    st.session_state["search_message"] = None
    try:
        response = requests.get(f"{API_BASE_URL}/api/geocode",
                                params={"place_id": place_id}, timeout=REQUEST_TIMEOUT_SECONDS)
    except Exception as error:
        # Never surface a raw transport error; it can carry a URL with the key.
        st.session_state["search_message"] = ("error", f"Location search is unavailable ({type(error).__name__}).")
        return
    if response.status_code != 200:
        st.session_state["search_message"] = ("error", f"Location search failed (HTTP {response.status_code}).")
        return
    try:
        place = response.json()
        # The suggestion's own wording, not the geocoder's official name: picking
        # "Salt Lake City, Kolkata" and being shown "Bidhannagar" reads as a mis-pick.
        st.session_state["pending_coordinate"] = (place["lat"], place["lng"], description)
    except (ValueError, KeyError, TypeError):
        st.session_state["search_message"] = ("error", "Location search returned an unexpected response.")


def render_place_search(key, label=None, placeholder="e.g. Karol Bagh, Delhi"):
    """Typeahead over Google Places. Both instances share one coordinate."""
    try:
        from streamlit_searchbox import st_searchbox
    except ImportError:
        st.caption("Place search unavailable. Use the shortcut or type coordinates.")
        return

    chosen = st_searchbox(
        fetch_place_suggestions,
        key=key,
        label=label,
        placeholder=placeholder,
        # Seeds the box with the active place, which is how the two stay in step.
        default_searchterm=st.session_state.get("resolved_place") or "",
        edit_after_submit="option",
        debounce=SEARCH_DEBOUNCE_MS,
    )
    if chosen:
        select_place(chosen)
        if st.session_state.get("pending_coordinate"):
            st.rerun()


def describe_point(latitude, longitude):
    """Name a clicked point so the box reads as a place, not as a bare click."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/geocode/reverse",
                                params={"lat": latitude, "lng": longitude},
                                timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code != 200:
            return MAP_CLICK_FALLBACK_LABEL
        named = response.json()
        return named.get("formatted_address") or MAP_CLICK_FALLBACK_LABEL
    except Exception:
        # A nameless point is still analysable, so never fail the click over this.
        return MAP_CLICK_FALLBACK_LABEL


def render_location_picker():
    """World map where a click chooses the coordinate to analyse."""
    try:
        import folium
        from streamlit_folium import st_folium
    except ImportError:
        st.caption("Map picker unavailable. Use the shortcut, search, or type coordinates.")
        return

    try:
        latitude = float(st.session_state.get("imagery_latitude"))
        longitude = float(st.session_state.get("imagery_longitude"))
    except (TypeError, ValueError):
        latitude, longitude = next(iter(CITY_COORDINATES.values()))

    world = folium.Map(location=[latitude, longitude], zoom_start=11, control_scale=True)
    # A vector marker, not folium's default pin: the pin's icon PNG is fetched
    # from a CDN that browsers block, which renders a broken image over the map.
    folium.CircleMarker([latitude, longitude], radius=9, tooltip="Selected location",
                        color="#ff4d4f", weight=3, fill=True,
                        fill_color="#ff4d4f", fill_opacity=0.45).add_to(world)
    clicked = st_folium(world, height=320, width=None, key="location_picker",
                        returned_objects=["last_clicked"])

    point = (clicked or {}).get("last_clicked") or {}
    new_latitude, new_longitude = point.get("lat"), point.get("lng")
    if new_latitude is None or new_longitude is None:
        return
    # Folium can report a longitude beyond ±180 when the world map is panned
    # across the date line; the backend rejects those, so never send them.
    if not (-90 <= new_latitude <= 90) or not (-180 <= new_longitude <= 180):
        st.warning("That point is outside the valid coordinate range.")
        return
    if (f"{new_latitude:.6f}", f"{new_longitude:.6f}") != (
        st.session_state.get("imagery_latitude"), st.session_state.get("imagery_longitude")
    ):
        # The picker renders after the sidebar's coordinate inputs exist, and a
        # widget key cannot be written once its widget is instantiated. Hand the
        # click to the next run, which applies it before any widget is created.
        st.session_state["pending_coordinate"] = (
            new_latitude, new_longitude, describe_point(new_latitude, new_longitude))
        st.rerun()


def apply_pending_coordinate():
    """Apply a deferred map click. Must run before the coordinate widgets exist."""
    pending = st.session_state.pop("pending_coordinate", None)
    if pending:
        set_coordinates(*pending)
        # Dropping their state makes both typeaheads re-seed from resolved_place,
        # so two boxes can never show different places for one coordinate.
        for searchbox in SEARCHBOX_KEYS:
            st.session_state.pop(searchbox, None)


st.set_page_config(
    page_title="HotSpot Sentinels", page_icon=":material/landscape:",
    layout="wide", initial_sidebar_state="expanded",
)

st.title("HotSpot Sentinels")
st.caption("Name a place. See its urban heat risk.")

# Before any widget is created, so a deferred map click can write its keys.
apply_pending_coordinate()

with st.sidebar:
    st.header("Analysis inputs")
    analysis_mode = st.segmented_control(
        "Analysis source", [MODE_LOCATION, MODE_UPLOAD],
        default=MODE_LOCATION, key="analysis_mode",
    )
    use_temperature_override = st.toggle("Use what-if temperature", value=False)
    ambient_temp_c = None
    if use_temperature_override:
        ambient_temp_c = st.number_input(
            "What-if ambient temperature (°C)", min_value=-50.0, max_value=60.0,
            value=35.0, step=0.5, key="ambient_temp_override",
        )
        st.warning("What-if input · Climate telemetry will not be queried.")
    else:
        st.caption("Temperature: backend climate telemetry")
    uploaded_file = None
    if analysis_mode == MODE_LOCATION:
        st.selectbox(
            "Location shortcut", [*CITY_COORDINATES, "Custom coordinates"],
            key="location_preset", on_change=apply_location_preset,
        )
        opening_latitude, opening_longitude = next(iter(CITY_COORDINATES.values()))
        st.session_state.setdefault("imagery_latitude", str(opening_latitude))
        st.session_state.setdefault("imagery_longitude", str(opening_longitude))

        render_place_search(SEARCHBOX_KEYS[0], "Search a city or area")
        message = st.session_state.get("search_message")
        if message:
            level, text = message
            (st.error if level == "error" else st.warning)(text)
        elif st.session_state.get("resolved_place"):
            st.success(st.session_state["resolved_place"], icon=":material/place:")

        st.text_input("Latitude", key="imagery_latitude", placeholder="-90 to 90")
        st.text_input("Longitude", key="imagery_longitude", placeholder="-180 to 180")
        st.caption("Coordinates are sent to the backend; imagery is retrieved server-side.")
    else:
        uploaded_file = st.file_uploader("Upload urban aerial photo", type=["jpg", "jpeg", "png"])
        try:
            presets = sorted(path for path in SAMPLE_DIRECTORY.glob("*") if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png"})
        except OSError as error:
            logger.warning("Preset discovery failed: %s", type(error).__name__)
            presets = []
        preset_name = st.selectbox("Preset image", ["Choose a preset"] + [path.name for path in presets])
        if not presets:
            st.info("No preset images available. Run `python backend/tools/seed_samples.py`; custom upload is still available.")
        if uploaded_file is None and preset_name != "Choose a preset":
            try:
                preset_path = SAMPLE_DIRECTORY / preset_name
                uploaded_file = io.BytesIO(load_preset(str(preset_path), preset_path.stat().st_mtime_ns))
                uploaded_file.name = preset_name
            except (OSError, ValueError) as error:
                logger.warning("Preset loading failed: %s", type(error).__name__)
                st.error("Preset image unavailable. Choose another image or upload a JPEG or PNG.")
    st.divider()
    st.subheader("Backend readiness")
    if st.button("Check backend health", icon=":material/monitor_heart:"):
        try:
            with st.spinner("Checking backend dependencies..."):
                health_response = requests.get(f"{API_BASE_URL}/api/health", timeout=REQUEST_TIMEOUT_SECONDS)
            if health_response.status_code == 200:
                health = health_response.json()
                if health.get("status") == "degraded":
                    st.warning("Backend degraded. Some dependencies are unavailable; analysis, persistence or alerts may fail.")
                elif health.get("status") == "operational":
                    st.success("Backend operational.")
                else:
                    st.info("Backend readiness unavailable.")
                for dependency, state in (health.get("dependencies") or {}).items():
                    st.text(f"{dependency}: {display_value(state)}")
            else:
                render_response_error(health_response, "Backend health")
        except Exception as error:
            render_request_error(error, "Backend health")

image_ready = False
if analysis_mode == "Upload image" and uploaded_file is not None:
    try:
        content_type = mimetypes.guess_type(uploaded_file.name)[0] or JPEG_MIME_TYPE
        image_bytes = uploaded_file.getvalue()
        if len(image_bytes) > MAX_UPLOAD_BYTES:
            st.error("Image exceeds the 10,000,000-byte upload limit (HTTP 413). Choose a smaller JPEG or PNG.")
        elif Path(uploaded_file.name).suffix.lower() not in {".jpg", ".jpeg", ".png"} or content_type not in {JPEG_MIME_TYPE, "image/png"}:
            st.error("Unsupported image type (HTTP 415). Upload a JPEG or PNG.")
        elif not ((content_type == JPEG_MIME_TYPE and image_bytes.startswith(b"\xff\xd8\xff")) or (content_type == "image/png" and image_bytes.startswith(b"\x89PNG\r\n\x1a\n"))):
            st.error("Image content does not match its JPEG or PNG filename (HTTP 415). Choose a valid image.")
        else:
            image = Image.open(io.BytesIO(image_bytes))
            image.load()
            image_ready = True
    except Exception as error:
        logger.warning("Image preview failed: %s", type(error).__name__)
        st.error("Image could not be opened. Upload a valid JPEG or PNG.")

files = (
    {"file": (uploaded_file.name, uploaded_file.getvalue(), content_type)}
    if uploaded_file is not None else None
)

if analysis_mode == MODE_LOCATION:
    try:
        latitude = float(st.session_state["imagery_latitude"])
        longitude = float(st.session_state["imagery_longitude"])
        coordinates_valid = (
            math.isfinite(latitude) and math.isfinite(longitude)
            and -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0
        )
    except (TypeError, ValueError):
        latitude = longitude = None
        coordinates_valid = False
    analysis_identity = ("location", latitude, longitude) if coordinates_valid else None
    analysis_ready = coordinates_valid
elif image_ready:
    analysis_identity = ("upload", uploaded_file.name, image_bytes)
    analysis_ready = True
else:
    analysis_identity = None
    analysis_ready = False

if st.session_state.get("analysis_identity") != analysis_identity:
    st.session_state.pop("analysis_result", None)
    st.session_state.pop("satellite_imagery_identity", None)
    st.session_state.pop("satellite_imagery_bytes", None)

if analysis_ready:
    image_column, score_column = st.columns([1, 1.2])
    with image_column:
        if analysis_mode == MODE_UPLOAD:
            st.subheader("Aerial inspection")
            st.image(image, caption=uploaded_file.name, width="stretch")
        else:
            st.subheader("Selected location")
            st.text(f"Latitude: {latitude} | Longitude: {longitude}")
            with st.expander("Pick a location on the map", icon=":material/map:"):
                render_place_search(SEARCHBOX_KEYS[1], placeholder="Search here, or click the map")
                render_location_picker()
            satellite_preview = st.empty()
    with score_column:
        st.subheader("Heat risk assessment")
        if st.button("Run HotSpot Analysis", type="primary", width="stretch", icon=":material/play_arrow:"):
            st.session_state.pop("analysis_result", None)
            with st.spinner("Analyzing surface materials, checking climate telemetry and preparing the cooling blueprint..."):
                try:
                    if ambient_temp_c is not None and (not math.isfinite(ambient_temp_c) or not -50.0 <= ambient_temp_c <= 60.0):
                        raise ValueError("Invalid temperature input")
                    form_fields = {"ambient_temp_c": ambient_temp_c} if use_temperature_override else {}
                    if analysis_mode == MODE_LOCATION:
                        form_fields.update({"imagery_lat": latitude, "imagery_lng": longitude})
                    response = requests.post(
                        f"{API_BASE_URL}/api/analyze", files=files,
                        data=form_fields, timeout=REQUEST_TIMEOUT_SECONDS,
                    )
                    if response.status_code == 200:
                        result = response.json()
                        if not isinstance(result, dict):
                            raise ValueError("Invalid report")
                        st.session_state["analysis_identity"] = analysis_identity
                        st.session_state["analysis_result"] = result
                    else:
                        render_response_error(response, "Analysis")
                except Exception as error:
                    render_request_error(error, "Analysis")
        report = st.session_state.get("analysis_result")
        if report is not None:
            render_critical_alert(report)
            render_image_source(report)
            render_score(report)
        else:
            st.info("Choose a location or image, then run the analysis.")
    if report is not None and analysis_mode == MODE_LOCATION and report.get("image_source") == "google_maps":
        imagery_identity = ("location-imagery", latitude, longitude)
        imagery_bytes = (
            st.session_state.get("satellite_imagery_bytes")
            if st.session_state.get("satellite_imagery_identity") == imagery_identity
            else None
        )
        if imagery_bytes is None:
            try:
                with st.spinner("Loading satellite imagery..."):
                    imagery_response = requests.get(
                        f"{API_BASE_URL}/api/imagery",
                        params={"lat": latitude, "lng": longitude},
                        timeout=REQUEST_TIMEOUT_SECONDS,
                    )
                response_content = imagery_response.content
                if imagery_response.status_code == 200 and isinstance(response_content, bytes) and response_content:
                    try:
                        with Image.open(io.BytesIO(response_content)) as satellite_image:
                            satellite_image.verify()
                        imagery_bytes = response_content
                        st.session_state["satellite_imagery_identity"] = imagery_identity
                        st.session_state["satellite_imagery_bytes"] = imagery_bytes
                    except (OSError, ValueError) as error:
                        logger.warning("Satellite imagery response invalid: %s", type(error).__name__)
                        render_satellite_imagery_unavailable(satellite_preview, report)
                elif imagery_response.status_code == 502:
                    logger.info("Satellite imagery unavailable: HTTP 502")
                    render_satellite_imagery_unavailable(satellite_preview, report)
                else:
                    logger.warning("Satellite imagery unavailable: HTTP %s", imagery_response.status_code)
                    render_satellite_imagery_unavailable(satellite_preview, report)
            except Exception as error:
                logger.warning("Satellite imagery request failed: %s", type(error).__name__)
                render_satellite_imagery_unavailable(satellite_preview, report)
        if imagery_bytes is not None:
            with satellite_preview.container():
                st.image(imagery_bytes, width="stretch")
                if report.get("attribution_required") is True:
                    st.caption("Imagery from Google Maps")
    if report is not None:
        render_blueprint(report)
elif analysis_mode == MODE_LOCATION:
    st.error("Coordinates must be finite and within latitude -90 to 90 and longitude -180 to 180.")
else:
    st.info("Select a preset or upload an aerial JPEG or PNG to begin.")

st.divider()
st.subheader("Recent municipal audits")
def render_city_map(scans):
    """Plot every scan that carries coordinates, coloured by risk band."""
    points = []
    for scan in scans:
        # Only coordinates the caller actually asked for are real. For an uploaded
        # image the model infers a plausible-looking location, which has put zones
        # in Los Angeles; plotting those would make the map meaningless.
        if scan.get("image_source") != "google_maps":
            continue
        coordinates = scan.get("coordinates") or {}
        latitude, longitude = coordinates.get("lat"), coordinates.get("lng")
        # A scan without coordinates is an uploaded image, not a located zone.
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            continue
        if isinstance(latitude, bool) or isinstance(longitude, bool):
            continue
        score = scan.get("hvi_score")
        points.append({
            "lat": float(latitude),
            "lon": float(longitude),
            "colour": MAP_RISK_COLOURS.get(scan.get("risk_level"), "#8b9aad"),
            # Area scales with risk so the worst zones read first at a glance.
            "size": 120 + 40 * (float(score) if isinstance(score, (int, float)) and not isinstance(score, bool) else 0),
        })

    if not points:
        st.info("No located scans yet. Analyse a coordinate to put a zone on the map.")
        return

    # Without an explicit zoom, st.map frames the whole world for a handful of
    # nearby points, which renders the markers as unreadable specks.
    latitudes = [point["lat"] for point in points]
    longitudes = [point["lon"] for point in points]
    spread = max(max(latitudes) - min(latitudes), max(longitudes) - min(longitudes))
    for threshold, level in ((0.05, 13), (0.2, 11), (1.0, 9), (5.0, 6), (20.0, 4)):
        if spread <= threshold:
            zoom = level
            break
    else:
        zoom = 2

    st.map(points, latitude="lat", longitude="lon", color="colour", size="size", zoom=zoom)
    legend = " · ".join(f"{band} {colour}" for band, colour in MAP_RISK_COLOURS.items())
    st.caption(f"Marker colour by risk band — {legend}. Marker size scales with HVI.")


if st.button("Refresh Recent Audits", icon=":material/refresh:"):
    try:
        with st.spinner("Loading recent audits..."):
            history_res = requests.get(f"{API_BASE_URL}/api/scans?limit=5", timeout=REQUEST_TIMEOUT_SECONDS)
        if history_res.status_code == 200:
            scans = history_res.json().get("scans") or []
            if scans:
                with st.container(border=True):
                    st.subheader("City-wide heat map", divider="grey")
                    render_city_map(scans)
                rows = []
                for scan in scans:
                    rows.append({
                        "Zone": display_value(scan.get("zone_name")),
                        "HVI": display_value(scan.get("hvi_score")),
                        "Risk": display_value(scan.get("risk_level")),
                        "Ambient (°C)": display_value(scan.get("ambient_temp_c")),
                        "Climate source": display_value(scan.get("climate_source")),
                        "Recorded": display_value(scan.get("timestamp")),
                    })
                st.dataframe(rows, hide_index=True, width="stretch")
                for scan in scans:
                    with st.expander(f"{display_value(scan.get('zone_name'))} | HVI: {display_value(scan.get('hvi_score'))} ({display_value(scan.get('risk_level'))})"):
                        render_critical_alert(scan)
                        plan = scan.get("passive_cooling_plan") or {}
                        st.text(f"Recorded ambient: {display_value(scan.get('ambient_temp_c'), ' °C')} | Projected cooling drop: {display_value(plan.get('projected_surface_temp_drop_c'), ' °C')}")
                        dispatched = scan.get("alert_dispatched")
                        dispatch_status = "-"
                        if dispatched is True:
                            dispatch_status = "Confirmed"
                        elif dispatched is False:
                            dispatch_status = "Not confirmed"
                        st.text(f"Pub/Sub alert dispatched: {dispatch_status}")
                        st.text(f"Alert attempted: {display_value(scan.get('alert_attempted'))}")
                        st.text(f"Document ID: {display_value(scan.get('doc_id'))}")
                        render_surface_chart(scan.get("surface_breakdown") or {})
            else:
                st.info("No prior scans found in Firestore.")
        else:
            render_response_error(history_res, "Audit history")
    except Exception as error:
        render_request_error(error, "Audit history")
