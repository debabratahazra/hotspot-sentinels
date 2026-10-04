---
name: "Vision Analyzer Module"
description: "Scaffold backend/services/vision_analyzer.py: the Gemini 2.5 Flash multimodal module that scores urban Heat Vulnerability Index (HVI) from aerial imagery and returns the Heat Analysis Result JSON."
argument-hint: "Optional: extra fields, zone defaults, or rubric tweaks"
agent: "agent"
tools: ["edit", "search", "problems"]
---

Implement the multimodal vision inference module for HotSpot Sentinels (Epic 1 / Story 1.1).

Authoritative spec: [COPILOT_GUIDE.md](../../COPILOT_GUIDE.md). Follow its hard technical constraints and reproduce the **Heat Analysis Result Schema** field-for-field.

## Target file

`backend/services/vision_analyzer.py`

## Required public API

```python
async def analyze_urban_hotspot(image_bytes: bytes, ambient_temp: float, zone_name: str) -> dict
```

## Implementation rules

- Use `from google import genai` / `from google.genai import types` with `genai.Client(vertexai=True, project=..., location=...)`. Never import `vertexai.generative_models`.
- Read config from env: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_REGION` (default `asia-southeast1`), `MODEL_ID` (default `gemini-2.5-flash`). Build the client lazily and cache it at module level.
- Send the image as an inline part (`types.Part.from_bytes`) next to the text prompt; sniff or accept the mime type rather than hardcoding a wrong one.
- Put the urban-climatologist persona and the scoring rubric in `system_instruction`. Force structured output with `response_mime_type="application/json"` plus an explicit `response_schema` mirroring the guide's schema.
- Rubric the model must follow:
  - `hvi_score` is a float from 1.0 to 10.0.
  - `risk_level` is derived from HVI: `LOW` < 4.0, `MODERATE` 4.0–5.9, `HIGH` 6.0–7.9, `CRITICAL` >= 8.0.
  - `surface_breakdown` percentages are integers that sum to 100.
  - `passive_cooling_plan.corridor_orientation` names a compass axis and justifies it with prevailing monsoon wind direction.
  - All units metric (°C, m, m², km²).
- Keep the route async-safe: run the blocking SDK call via `asyncio.to_thread`.
- Parse the JSON response, then normalize: inject `zone_name`, `ambient_temp_c`, a generated `zone_id`, and a UTC ISO-8601 `timestamp`. Leave `alert_dispatched` to the caller.
- Raise a module-level `VisionAnalysisError` on API failure or unparseable output instead of returning half-filled dicts.
- Never log raw image bytes, credentials, or full request payloads.

## Done when

- The module is import-only (no top-level side effects beyond config reads) and reports zero diagnostics.
- The returned dict validates against every key in the guide's schema.
