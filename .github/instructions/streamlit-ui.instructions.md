---
name: "Streamlit Dashboard"
description: "Use when writing or changing the HotSpot Sentinels Streamlit frontend — dark theme, HVI badges, charts, sidebar controls, API calls, caching, or error states. Covers the presentation-layer boundary and the visual contract."
applyTo: ["frontend/**/*.py", "frontend/.streamlit/*.toml"]
---

# Streamlit Dashboard Rules

## Boundary

The dashboard renders what the API returns. It never:

- recalculates HVI, converts units, or re-derives `risk_level`;
- imports `google.cloud.*` or `google.genai` — no direct cloud calls from the UI;
- hardcodes a project ID, bucket name, or deployed Cloud Run URL.

API base URL comes from `API_BASE_URL`, defaulting to `http://localhost:8080`.

## Visual contract

Badge colour is a pure function of `hvi_score`, and the boundaries match the backend exactly:

| HVI     | Badge                                   |
| ------- | --------------------------------------- |
| < 4.0   | green (`LOW`)                           |
| 4.0–5.9 | green (`MODERATE`)                      |
| 6.0–7.9 | amber (`HIGH`)                          |
| >= 8.0  | red (`CRITICAL`) + Pub/Sub alert banner |

Surface breakdown keeps one colour per material across every chart: asphalt dark grey, dark roof near-black, concrete light grey, green canopy green.

Display metric units only — °C and m².

## Conventions

- `st.set_page_config(page_title="HotSpot Sentinels", layout="wide")` runs before any other Streamlit call.
- Theme via `frontend/.streamlit/config.toml` (`base = "dark"`). Use injected CSS only for what the theme cannot express.
- Prefer native components over raw HTML. Never render API strings through `unsafe_allow_html=True` — that is an XSS vector.
- Cache preset image loading with `@st.cache_data`; never cache the analysis request itself.
- Wrap requests in `st.spinner` and set an explicit `timeout=` on every call.

## Degraded states

Each of these renders a friendly `st.error` or `st.info`, never a traceback:

| Condition                             | Message                                                              |
| ------------------------------------- | -------------------------------------------------------------------- |
| API unreachable                       | "Backend unavailable — start it with `uvicorn main:app --port 8080`" |
| Non-200 response                      | Show the status code and a generic message, not the response body    |
| No presets in `data_samples/`         | Point at `python backend/tools/seed_samples.py`                      |
| Report missing `passive_cooling_plan` | Render the rest, flag the gap                                        |

Never surface a stack trace or a cloud resource path to the user.
