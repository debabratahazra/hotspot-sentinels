---
name: heat-report-validation
description: "Validate that a Heat Analysis Result payload matches the HotSpot Sentinels contract. Use when checking Gemini output, a POST /api/analyze response, a Firestore document, or a Pydantic/response_schema definition against the canonical schema — and when HVI score, risk_level band, surface percentage totals, metric units, or alert thresholds look wrong or drift between layers."
argument-hint: "Path to a report JSON file, or the layer to audit (vision_analyzer | main.py | frontend)"
---

# Heat Analysis Result Validation

The Heat Analysis Result schema in [COPILOT_GUIDE.md](../../../COPILOT_GUIDE.md) is the contract four layers must agree on:

| Layer                                 | Where the contract appears                           |
| ------------------------------------- | ---------------------------------------------------- |
| `backend/services/vision_analyzer.py` | Gemini `response_schema` + system instruction rubric |
| `backend/main.py`                     | Pydantic response model                              |
| `backend/services/database.py`        | Firestore document written to `hotspot_scans`        |
| `frontend/app.py`                     | Badge thresholds and blueprint fields                |

Drift between them is the most common bug in this project. This skill checks a payload and, when asked, audits the layers that produce it.

## When to use

- A `/api/analyze` response, Firestore document, or captured Gemini output needs checking.
- The UI badge colour disagrees with the HVI number.
- Surface percentages do not add up, or a field appears in imperial units.
- You changed the schema in one layer and need to propagate it.

## Validate a payload

```bash
python .github/skills/heat-report-validation/scripts/validate_report.py path/to/report.json
# or pipe it
curl -s -X POST http://localhost:8080/api/analyze -F "image=@data_samples/industrial_asphalt.png" -F "ambient_temp=36.5" \
  | python .github/skills/heat-report-validation/scripts/validate_report.py -
```

The [validator](./scripts/validate_report.py) is stdlib-only and exits non-zero on failure. It enforces the structural rules in [heat_analysis_result.schema.json](./assets/heat_analysis_result.schema.json) plus these cross-field rules:

- `surface_breakdown` percentages total exactly 100.
- `risk_level` matches the `hvi_score` band: `LOW` < 4.0, `MODERATE` 4.0–5.9, `HIGH` 6.0–7.9, `CRITICAL` >= 8.0.
- `timestamp` parses as ISO-8601.
- `alert_dispatched` is never `true` below the 8.0 dispatch threshold.

Extra keys are allowed at the root (the API adds envelope fields like `doc_id`), but nested objects are closed.

## Audit a layer

1. Read the layer's definition of the schema — `response_schema`, the Pydantic model, or the field names the UI reads.
2. Compare field-by-field against [the schema asset](./assets/heat_analysis_result.schema.json): names, nesting, types, and the four `risk_level` values.
3. Check units are metric — `_c` fields in Celsius, `_sqm` in m². Flag any Fahrenheit, feet, or square-foot values and convert at the source.
4. Confirm the HVI band boundaries are identical everywhere. Extract them to one shared constant if they are duplicated inline.
5. Report each mismatch with the file and the correct value; fix only what the user confirms.

## Fixing a failure

| Failure                  | Fix at                                                                       |
| ------------------------ | ---------------------------------------------------------------------------- |
| Missing or misnamed key  | `response_schema` in `vision_analyzer.py` — do not patch it in the API layer |
| Percentages ≠ 100        | Strengthen the system instruction, then normalize defensively after parsing  |
| `risk_level` mismatch    | Derive it from `hvi_score` in code rather than trusting the model            |
| Non-metric value         | Convert at the service boundary, never in the UI                             |
| `alert_dispatched` wrong | Set it from the Pub/Sub message ID returned by `dispatch_heat_alert`         |

## Done when

The validator prints `PASS` and every audited layer names the same fields, units, and thresholds.
