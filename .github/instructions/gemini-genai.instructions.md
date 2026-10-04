---
name: "Gemini GenAI SDK"
description: "Use when calling Gemini, building multimodal prompts, sending images to Vertex AI, configuring system instructions, or enforcing structured JSON output with the google.genai SDK. Covers vision_analyzer, HVI scoring, and response schemas."
applyTo: ["backend/services/vision_analyzer.py", "backend/verify_setup.py"]
---

# Gemini / google.genai Rules

## Client

Only the modern unified SDK. Legacy `vertexai.generative_models` and `google.generativeai` are forbidden.

```python
from google import genai
from google.genai import types

client = genai.Client(
    vertexai=True,
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_REGION", "asia-southeast1"),
)
```

Build the client once at module level, lazily. Model id always from `os.getenv("MODEL_ID", "gemini-2.5-flash")`.

## Multimodal requests

- Images go inline as `types.Part.from_bytes(data=image_bytes, mime_type=...)`; pass the caller's real mime type rather than assuming PNG.
- Persona, rubric, and output contract belong in `config=types.GenerateContentConfig(system_instruction=...)`, not prepended to user content.
- Never echo image bytes or the full prompt into logs.

## Structured output

Never parse JSON out of prose. Force it:

```python
config=types.GenerateContentConfig(
    system_instruction=SYSTEM_INSTRUCTION,
    response_mime_type="application/json",
    response_schema=HEAT_ANALYSIS_SCHEMA,
    temperature=0.2,
)
```

The schema must match the Heat Analysis Result Schema in [COPILOT_GUIDE.md](../../COPILOT_GUIDE.md) exactly — same keys, same nesting, metric units.

## HVI rubric

Keep these thresholds identical in the system instruction, the API, and the UI:

| HVI     | risk_level |
| ------- | ---------- |
| < 4.0   | `LOW`      |
| 4.0–5.9 | `MODERATE` |
| 6.0–7.9 | `HIGH`     |
| >= 8.0  | `CRITICAL` |

`hvi_score` is a float 1.0–10.0. `surface_breakdown` percentages are integers summing to 100. `corridor_orientation` names a compass axis justified by prevailing monsoon winds.

## Async and errors

`generate_content` is blocking — call it through `asyncio.to_thread` from async code. Wrap SDK and JSON-decode failures in `VisionAnalysisError`; never return a partially populated result dict.
