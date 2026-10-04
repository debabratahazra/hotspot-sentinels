# EPIC-07 — Interactive Dashboard & Heat Visualizer

|                |                                                                                                                                                       |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Goal**       | Make urban heat risk obvious in ten seconds: an aerial image, an HVI badge, a passive cooling blueprint, and an alert banner when a zone is critical. |
| **Source**     | [Epics_Stories.md](../../../Epics_Stories.md) Epic 5                                                                                                  |
| **Priority**   | P1                                                                                                                                                    |
| **Status**     | Not started                                                                                                                                           |
| **Depends on** | EPIC-05                                                                                                                                               |
| **Delivers**   | `frontend/app.py`, `frontend/.streamlit/config.toml`                                                                                                  |

## Why this epic exists

This is the only part of the project a judge will actually look at. Everything else is plumbing that earns the right to show this screen.

## Scope

**In:** layout, theming, charts, controls, API calls, loading and error states.

**Out:** any computation. The dashboard renders what `/api/analyze` returns — it never recalculates HVI, converts units, re-derives `risk_level`, or talks to Google Cloud directly.

## Visual contract

Badge colour is a pure function of `hvi_score`, with boundaries identical to the backend:

| HVI     | Badge | Label                     |
| ------- | ----- | ------------------------- |
| < 4.0   | green | `LOW`                     |
| 4.0–5.9 | green | `MODERATE`                |
| 6.0–7.9 | amber | `HIGH`                    |
| >= 8.0  | red   | `CRITICAL` + alert banner |

Surface materials keep one colour across every chart: asphalt dark grey, dark roof near-black, concrete light grey, green canopy green. All units metric.

## Stories

### Story 7.1 — Shell, theme and sidebar controls
- **Files:** `frontend/app.py`, `frontend/.streamlit/config.toml`
- **Estimate:** 3 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] `st.set_page_config(page_title="HotSpot Sentinels", layout="wide")` before any other Streamlit call
  - [ ] Dark theme via `config.toml` (`base = "dark"`)
  - [ ] City selector: Singapore, Bangkok, Delhi — each mapped to lat/lng defaults
  - [ ] Ambient temperature slider 30.0–45.0 °C, default 36.5, step 0.5
  - [ ] Preset picker reading `data_samples/` plus a custom `st.file_uploader`
  - [ ] "Run Analysis" posts multipart form data to `{API_BASE_URL}/api/analyze`
  - [ ] `API_BASE_URL` from env, default `http://localhost:8080`; no hardcoded project IDs or deployed URLs

### Story 7.2 — HVI score panel
- **File:** `frontend/app.py`
- **Estimate:** 3 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Two columns: the aerial image left, the score right
  - [ ] HVI rendered as a large metric with a coloured badge matching the visual contract exactly
  - [ ] Ambient temperature shown in °C alongside its provenance from `climate_source`
  - [ ] Badge thresholds never rounded or reinterpreted in the UI

### Story 7.3 — Passive cooling blueprint
- **File:** `frontend/app.py`
- **Estimate:** 3 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Surface breakdown as a bar or donut chart with the fixed material colours
  - [ ] Recommended wind-corridor orientation displayed prominently
  - [ ] Retroreflective coating area in m² and projected temperature drop in °C
  - [ ] Micro-canopy interventions rendered as a checklist
  - [ ] Recent scans table fed by `GET /api/scans`

### Story 7.4 — Critical alert banner
- **File:** `frontend/app.py`
- **Estimate:** 1 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] When `hvi_score >= 8.0`, a prominent `st.error` banner confirms the automated Pub/Sub notification was dispatched
  - [ ] The banner reflects the real `alert_dispatched` value — it never claims an alert that did not happen
  - [ ] No banner below the threshold

### Story 7.5 — Degraded states
- **File:** `frontend/app.py`
- **Estimate:** 2 · **Priority:** P2 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] API unreachable → friendly `st.error` naming the uvicorn command, never a traceback
  - [ ] Non-200 response → status code and a generic message, not the raw response body
  - [ ] Slow analysis → `st.spinner`, with an explicit `timeout=` on every request
  - [ ] No presets in `data_samples/` → points at `seed_samples.py`
  - [ ] Report missing `passive_cooling_plan` → renders the rest and flags the gap
  - [ ] Preset image loading cached with `@st.cache_data`; the analysis request itself never cached
  - [ ] API strings never rendered through `unsafe_allow_html=True`

## Definition of done

`streamlit run frontend/app.py` renders without errors, a full round trip populates every section, the critical path shows the alert banner, and each degraded state has been exercised with a screenshot.

## Risks

| Risk                                           | Mitigation                                                      |
| ---------------------------------------------- | --------------------------------------------------------------- |
| Badge colour disagreeing with the backend band | Thresholds audited every sprint by the `contract-auditor` agent |
| Business logic creeping into the UI            | Layering rule in the `streamlit-ui` instructions                |
| XSS via `unsafe_allow_html` on API strings     | Native components only                                          |
| Tracebacks shown during the demo               | Story 7.5 is a requirement, not polish                          |
| Backend field renamed, UI silently blank       | Contract validation plus the recent-scans smoke check           |

## Seed the backlog

```bash
bl() { python3 .github/skills/agile-sdlc-loop/scripts/backlog.py "$@"; }
bl add --type epic --title "Interactive Dashboard and Heat Visualizer" --priority P1 \
  --description "Dark-themed Streamlit dashboard: HVI badge, cooling blueprint, alert banner"
bl add --type story --parent EPIC-007 --priority P1 --estimate 3 --source requirements \
  --title "As an analyst I can choose a city, temperature and image and run an analysis" \
  --files frontend/app.py frontend/.streamlit/config.toml \
  --ac "dark theme applied" "city, slider and image controls present" "posts to API_BASE_URL/api/analyze"
bl add --type story --parent EPIC-007 --priority P1 --estimate 3 --source requirements \
  --title "As an analyst I can see the HVI score and risk level at a glance" \
  --files frontend/app.py \
  --ac "badge colour matches the HVI band exactly" "image and score side by side" "temperature shown in Celsius with provenance"
bl add --type story --parent EPIC-007 --priority P1 --estimate 3 --source requirements \
  --title "As a city planner I can read the passive cooling blueprint" \
  --files frontend/app.py \
  --ac "surface breakdown charted with fixed material colours" "corridor orientation shown" \
       "coating area in m2 and temperature drop in C" "interventions listed"
bl add --type story --parent EPIC-007 --priority P1 --estimate 1 --source requirements \
  --title "As an ops lead I see confirmation that a critical alert was dispatched" \
  --files frontend/app.py \
  --ac "banner shown only at hvi >= 8.0" "banner reflects the real alert_dispatched value"
bl add --type story --parent EPIC-007 --priority P2 --estimate 2 --source requirements \
  --title "As a user the dashboard stays readable when something goes wrong" \
  --files frontend/app.py \
  --ac "friendly error when the API is unreachable" "no tracebacks rendered" "spinner during analysis"
```
