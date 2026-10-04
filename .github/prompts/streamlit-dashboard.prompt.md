---
name: "Streamlit Heat Dashboard"
description: "Scaffold frontend/app.py: the dark-themed Streamlit dashboard with city selector, temperature simulation slider, HVI gauge, passive cooling blueprint, and critical alert banner."
argument-hint: "Optional: extra cities, chart types, or layout changes"
agent: "agent"
tools: ["edit", "search", "runCommands", "problems"]
---

Build the interactive heat visualizer for HotSpot Sentinels (Epic 5 / Story 5.1).

Project rules: [COPILOT_GUIDE.md](../../COPILOT_GUIDE.md). The UI consumes the FastAPI service from Epic 4.

## Target file

`frontend/app.py`

## Layout

**Sidebar**

- City selector: Singapore, Bangkok, Delhi (each mapped to lat/lng defaults).
- Ambient temperature simulation slider: 30.0–45.0 °C, default 36.5, step 0.5.
- Image source: preset picker reading from `data_samples/` plus a custom `st.file_uploader`.
- "Run Analysis" button that POSTs multipart form data to `{API_BASE_URL}/api/analyze`.

**Main panel**

- Two columns: selected aerial image on the left; HVI score on the right as a large metric with a coloured badge — green `LOW`/`MODERATE`, amber `HIGH`, red `CRITICAL` — matching the guide's thresholds.
- **Passive Cooling Blueprint** section: surface breakdown (asphalt / dark roof / concrete / green canopy) as a bar or donut chart, recommended wind-corridor orientation, retroreflective coating m², and projected surface temperature drop in °C.
- Micro-canopy interventions rendered as a checklist.
- Recent scans table fed by `GET /api/scans`.

**Alert banner**

- When `hvi_score >= 8.0`, render a prominent `st.error` banner confirming the automated Pub/Sub emergency notification was dispatched.

## Implementation rules

- `st.set_page_config(page_title="HotSpot Sentinels", layout="wide")` and a dark theme via injected CSS; also add `frontend/.streamlit/config.toml` with `base = "dark"`.
- API base URL from `API_BASE_URL` env var, default `http://localhost:8080`. Never hardcode project IDs or secrets in the UI.
- Show `st.spinner` during the request; handle non-200 responses and connection errors with a friendly `st.error` instead of a traceback.
- Cache preset image loading with `@st.cache_data`.
- Display all units metric.

## Done when

- `streamlit run frontend/app.py` renders without errors and an analysis round-trip populates every section.
