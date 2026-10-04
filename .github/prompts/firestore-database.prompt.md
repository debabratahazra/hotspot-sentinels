---
name: "Firestore Report Store"
description: "Scaffold backend/services/database.py: persists hotspot scan reports to the Firestore 'hotspot_scans' collection and reads back the most recent scans."
argument-hint: "Optional: extra query filters or collection name"
agent: "agent"
tools: ["edit", "search", "problems"]
---

Build the Firestore persistence layer for HotSpot Sentinels (Epic 3 / Story 3.2).

Project rules: [COPILOT_GUIDE.md](../../COPILOT_GUIDE.md).

## Target file

`backend/services/database.py`

## Required public API

```python
def save_hotspot_report(report: dict) -> str
def get_recent_reports(limit: int = 10) -> list[dict]
```

## Implementation rules

- Use `google.cloud.firestore` with the project from `GOOGLE_CLOUD_PROJECT`; cache the client at module level. Collection name is a module constant `COLLECTION_NAME = "hotspot_scans"`.
- `save_hotspot_report` writes the full Heat Analysis Result document, sets `created_at` with `firestore.SERVER_TIMESTAMP` if `timestamp` is missing, and returns the generated document ID.
- `get_recent_reports` orders by `timestamp` descending, applies `limit`, and returns plain dicts with the Firestore document ID merged in as `zone_id` fallback / `doc_id`. Clamp `limit` to a sane range (1–100).
- Convert Firestore timestamp objects to ISO-8601 strings so results are JSON-serializable by FastAPI.
- On Firestore failure, log and re-raise a module-level `DatabaseError` so the API layer can map it to a 5xx response.
- Keep both functions synchronous; async routes wrap them with `asyncio.to_thread`.

## Done when

- Saving then reading returns the stored report, and every returned value is JSON-serializable.
