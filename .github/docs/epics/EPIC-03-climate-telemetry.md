# EPIC-03 — Climate Telemetry & Ingestion

|                |                                                                                                                                                    |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Goal**       | Ground Gemini's analysis in real ambient temperature readings, and degrade gracefully to realistic synthetic values when the cloud is unavailable. |
| **Source**     | [Epics_Stories.md](../../../Epics_Stories.md) Epic 2                                                                                               |
| **Priority**   | P2                                                                                                                                                 |
| **Status**     | Not started                                                                                                                                        |
| **Depends on** | EPIC-01                                                                                                                                            |
| **Delivers**   | `backend/tools/climate_service.py`                                                                                                                 |

## Why this epic exists

An HVI score computed against a guessed temperature is a demo, not a measurement. This epic supplies the one external fact the model cannot infer from a picture. It must never be able to break a request — hence the mandatory offline fallback.

## Scope

**In:** the BigQuery query against NOAA GSOD, Fahrenheit-to-Celsius conversion, sentinel filtering, and the offline fallback.

**Out:** forecasting, historical trend analysis, any second data source.

## Data notes

`bigquery-public-data.noaa_gsod.gsod2024` has two traps that will silently corrupt results:

- **Units are Fahrenheit.** `temp` and `max` are °F. The guide mandates metric, so convert at this boundary — never downstream.
- **`9999.9` is the missing-value sentinel.** Unfiltered, it converts to 5537.7 °C and poisons the analysis.

Default station `486980` is Singapore Changi.

## Stories

### Story 3.1 — Climate data retriever
- **File:** `backend/tools/climate_service.py`
- **Estimate:** 3 · **Priority:** P2 · **Status:** Not started
- **Source:** original Story 2.1
- **Required API:**
  ```python
  def get_latest_temperature(station_id: str = "486980") -> dict
  ```
  Returns `station_id`, `observation_date`, `max_temp_c`, `avg_temp_c`, `source`.
- **Acceptance criteria:**
  - [ ] Queries `bigquery-public-data.noaa_gsod.gsod2024` for the most recent valid row
  - [ ] `station_id` bound as a `bigquery.ScalarQueryParameter` — never string-formatted into SQL
  - [ ] `9999.9` sentinels filtered out before selection
  - [ ] Fahrenheit converted to Celsius; returned values are metric
  - [ ] `source` is `"bigquery"` on success
  - [ ] Client cached at module level; function stays synchronous for `asyncio.to_thread`

### Story 3.2 — Offline fallback
- **File:** `backend/tools/climate_service.py`
- **Estimate:** 2 · **Priority:** P2 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Credential, quota, network failure, or an empty result set returns a fallback reading instead of raising
  - [ ] `max_temp_c` between 35.0 and 41.0; `avg_temp_c` roughly 5–7 °C lower
  - [ ] `source` is `"fallback"` so callers and the UI can label the provenance
  - [ ] Logs a warning without leaking the raw cloud error payload
  - [ ] Only cloud and query exceptions are caught — `TypeError` and `KeyError` still surface as bugs
  - [ ] The function never raises to its caller

## Definition of done

Both paths return the documented dict shape, SQL is parameterised, units are Celsius, and EPIC-08 covers the conversion, the sentinel filter, and the fallback with mocked BigQuery.

## Risks

| Risk                                        | Mitigation                                                                        |
| ------------------------------------------- | --------------------------------------------------------------------------------- |
| Fahrenheit values reaching the UI           | Convert here; the `contract-auditor` agent checks for non-metric values           |
| `9999.9` sentinel treated as a real reading | Filter in the `WHERE` clause and assert it in tests                               |
| SQL injection via `station_id`              | `ScalarQueryParameter`; the `enforce-hard-constraints` hook warns on f-string SQL |
| BigQuery quota exhausted mid-demo           | The fallback makes this invisible to the user                                     |
| 2024 table goes stale                       | Parameterise the table year when the project outlives the dataset                 |

## Seed the backlog

```bash
bl() { python3 .github/skills/agile-sdlc-loop/scripts/backlog.py "$@"; }
bl add --type epic --title "Climate Telemetry and Ingestion" --priority P2 \
  --description "NOAA GSOD ambient temperature via BigQuery with an offline fallback"
bl add --type story --parent EPIC-003 --priority P2 --estimate 3 --source requirements \
  --title "As an analyst my zone score is grounded in a real ambient temperature" \
  --files backend/tools/climate_service.py \
  --ac "returns the most recent valid GSOD reading" \
       "station_id bound as a query parameter" \
       "9999.9 sentinels filtered" \
       "temperatures returned in Celsius"
bl add --type story --parent EPIC-003 --priority P2 --estimate 2 --source requirements \
  --title "As an operator the product still works when BigQuery is unavailable" \
  --files backend/tools/climate_service.py \
  --ac "cloud failure returns source=fallback" \
       "max_temp_c between 35 and 41" \
       "never raises to the caller"
```
