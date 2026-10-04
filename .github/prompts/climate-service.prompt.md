---
name: "Climate Telemetry Service"
description: "Scaffold backend/tools/climate_service.py: retrieves recent max/mean ambient temperature from the BigQuery NOAA GSOD public dataset with an offline summer-heat fallback."
argument-hint: "Optional: station id or target city"
agent: "agent"
tools: ["edit", "search", "problems"]
---

Build the climate telemetry retriever for HotSpot Sentinels (Epic 2 / Story 2.1).

Project rules: [COPILOT_GUIDE.md](../../COPILOT_GUIDE.md).

## Target file

`backend/tools/climate_service.py`

## Required public API

```python
def get_latest_temperature(station_id: str = "486980") -> dict
```

Station `486980` is Singapore Changi. Returned dict shape:

```python
{
    "station_id": "486980",
    "observation_date": "2024-07-14",   # ISO-8601 date
    "max_temp_c": 34.6,
    "avg_temp_c": 29.8,
    "source": "bigquery" | "fallback",
}
```

## Implementation rules

- Query `bigquery-public-data.noaa_gsod.gsod2024` via `google.cloud.bigquery`, ordering by date descending and limiting to the most recent valid row.
- Pass `station_id` as a `bigquery.ScalarQueryParameter` in `QueryJobConfig` — never string-format values into SQL.
- GSOD reports `temp` and `max` in Fahrenheit and uses `9999.9` as the missing sentinel. Filter sentinels out and convert to Celsius before returning; the guide mandates metric units everywhere.
- Fallback path: if credentials, quota, or network fail — or the query returns no rows — log a warning and return a deterministic-but-realistic tropical summer reading with `max_temp_c` between 35.0 and 41.0 and `avg_temp_c` roughly 5–7 °C lower, with `"source": "fallback"`.
- Catch only cloud/query exceptions for the fallback; do not swallow programming errors.
- Cache the BigQuery client at module level and keep the function synchronous — callers wrap it with `asyncio.to_thread`.

## Done when

- The function returns the documented dict shape in both the BigQuery and fallback paths, and never raises to the caller.
