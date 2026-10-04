---
name: "Pub/Sub Alert Dispatcher"
description: "Scaffold backend/services/alert_dispatcher.py: publishes urgent heat-resilience alerts to Pub/Sub when a zone's HVI score reaches the critical threshold."
argument-hint: "Optional: threshold override or extra payload fields"
agent: "agent"
tools: ["edit", "search", "problems"]
---

Build the event-driven alert publisher for HotSpot Sentinels (Epic 3 / Story 3.1).

Project rules: [COPILOT_GUIDE.md](../../COPILOT_GUIDE.md).

## Target file

`backend/services/alert_dispatcher.py`

## Required public API

```python
def dispatch_heat_alert(zone_data: dict) -> str
```

## Implementation rules

- Threshold: publish only when `zone_data["hvi_score"] >= 8.0` (expose it as a module constant `CRITICAL_HVI_THRESHOLD`). Below threshold, return an empty string without contacting Pub/Sub.
- Publish with `google.cloud.pubsub_v1.PublisherClient` to the topic named by `PUBSUB_TOPIC_ID` in project `GOOGLE_CLOUD_PROJECT`; build the path with `publisher.topic_path(...)`.
- Message payload is UTF-8 encoded JSON containing at minimum: `zone_id`, `zone_name`, `coordinates`, `ambient_temp_c`, `hvi_score`, `risk_level`, the urgent actions from `passive_cooling_plan.micro_canopy_interventions`, and a UTC ISO-8601 `dispatched_at`.
- Add Pub/Sub attributes `risk_level` and `zone_id` so subscribers can filter without decoding the body.
- Return the resolved message ID from `future.result(timeout=...)`.
- Treat dispatch as best-effort: on publish failure, log the error and return an empty string so the API request still succeeds. Do not let an alert failure break an analysis response.
- Never include credentials or raw imagery in the payload.

## Done when

- A sub-threshold dict returns `""` with no client call, and a critical dict returns a non-empty message ID.
