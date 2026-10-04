# Sprint 6 Report

Generated 2026-10-04T06:18:20+00:00
Goal: An analyst can analyse a real-world location from coordinates in the dashboard and receive a persisted, source-attributed heat report without an image upload.

## Delivery

- Committed: 4 item(s)
- Completed: 4
- Carried over: 0
- Open bugs: 0

| Item | Type | Priority | Status | Title |
|------|------|----------|--------|-------|
| STORY-034 | story | P1 | done | As an analyst I can fetch attributed satellite imagery for a coordinate |
| STORY-035 | story | P1 | done | As an analyst I can analyse a location without uploading an image |
| STORY-036 | story | P1 | done | As an analyst I can choose any location in the dashboard |
| STORY-037 | story | P1 | done | As an operator I can protect the Maps key and conserve imagery quota |

## Tests

- Result: **PASS**
- Summary: `607 passed, 3 warnings in 83.72s (0:01:23)`

## Coverage

- Configuration: `tests/coverage.ini` (backend application code)
- Total: **90.4%**

| File | Covered |
|------|---------|
| backend/main.py | 92.6% |
| backend/services/__init__.py | 100.0% |
| backend/services/alert_dispatcher.py | 100.0% |
| backend/services/database.py | 100.0% |
| backend/services/vision_analyzer.py | 100.0% |
| backend/tools/__init__.py | 100.0% |
| backend/tools/climate_service.py | 95.2% |
| backend/tools/maps_imagery_service.py | 37.8% |
| backend/tools/seed_samples.py | 98.9% |
| backend/verify_setup.py | 100.0% |

Below the 70% floor — needs test tasks next sprint:
- backend/tools/maps_imagery_service.py
