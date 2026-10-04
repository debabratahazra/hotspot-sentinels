---
name: "GCP Service Clients"
description: "Use when writing Firestore, Pub/Sub, BigQuery, or Cloud Storage code. Covers client construction, env-driven config, parameterized queries, graceful degradation, and offline fallbacks for the backend services and tools layers."
applyTo: ["backend/services/**/*.py", "backend/tools/**/*.py"]
---

# GCP Client Rules

Applies to `google.cloud.firestore`, `google.cloud.pubsub_v1`, `google.cloud.bigquery`, and `google.cloud.storage`.

## Client construction

- One cached module-level client per service, built lazily inside a `_get_client()` helper — not at import time, so modules import without credentials.
- Project from `GOOGLE_CLOUD_PROJECT`, region from `GOOGLE_CLOUD_REGION` (default `asia-southeast1`), bucket from `GCS_BUCKET_NAME`, topic from `PUBSUB_TOPIC_ID`. No hardcoded resource names.
- Authentication is Application Default Credentials only. Never construct clients from key files or inline secrets.

## Queries

Bind user-controlled values as query parameters — never f-string them into SQL:

```python
job_config = bigquery.QueryJobConfig(
    query_parameters=[bigquery.ScalarQueryParameter("station_id", "STRING", station_id)]
)
```

Validate and clamp caller-supplied limits (for example `limit` between 1 and 100) before passing them to Firestore or BigQuery.

## Units and serialization

- NOAA GSOD returns Fahrenheit and uses `9999.9` as the missing sentinel — filter sentinels and convert to Celsius before returning.
- Convert Firestore timestamps to ISO-8601 UTC strings so results are JSON-serializable by FastAPI.

## Failure policy

Match the criticality of the dependency:

| Service                 | On failure                                                                      |
| ----------------------- | ------------------------------------------------------------------------------- |
| BigQuery climate lookup | Log a warning, return the offline fallback reading with `"source": "fallback"`  |
| Pub/Sub alert           | Log the error, return `""` — a failed alert must not fail the analysis response |
| Firestore               | Raise `DatabaseError` so the API maps it to 503                                 |
| GCS upload in seeders   | Warn and continue with local files                                              |

Catch cloud/query exceptions specifically. Do not blanket-catch `Exception` in a way that hides `TypeError`/`KeyError` bugs, and never log raw credentials or full cloud error payloads.

## Async

These helpers stay synchronous; async callers use `asyncio.to_thread`.
