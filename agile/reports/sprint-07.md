# Sprint 7 Report

Generated 2026-10-04T18:17:57+00:00
Goal: An analyst can review coordinate-based heat reports with attributed imagery, while report validation, API safeguards and offline QA provide reliable evidence without cloud spend.

## Delivery

- Committed: 7 item(s), 15 point(s)
- Completed: 7
- Carried over: 0
- Open bugs: 0
- Authorised unplanned: 6 item(s), 12 point(s)
- **Revised total: 27 point(s)** against a 15-point commitment

| Item | Type | Priority | Status | Scope | Title |
|------|------|----------|--------|-------|-------|
| STORY-024 | story | P1 | done | committed | As a developer every API status code is covered |
| TASK-040 | task | P1 | done | committed | Checklist and validate every new report-envelope field |
| TASK-043 | task | P1 | done | committed | Budget for stale tests when a sprint deliberately changes behaviour |
| TASK-044 | task | P1 | done | committed | Prove attribution-required imagery is displayed by the dashboard |
| TASK-045 | task | P1 | done | committed | Require conclusive QA outcomes for long-running validation runs |
| TASK-047 | task | P2 | done | committed | Bound per-instance Maps request rate |
| TEST-002 | test | P2 | done | committed | Raise Maps imagery client coverage to the 70 percent floor |
| STORY-022 | story | P2 | done | unplanned | As a developer I can run the whole suite offline with one command |
| TASK-022 | task | P1 | done | unplanned | Align safe environment-template access with editor and secret guard policy |
| TASK-031 | task | P1 | done | unplanned | Obtain human decisions for validation, demo and performance limits |
| TASK-038 | task | P1 | done | unplanned | Retire legacy manual smoke scripts after migrating unique checks |
| BUG-025 | bug | P0 | done | unplanned | Cloud Run deploy script could never have produced a working revision |
| BUG-026 | bug | P0 | done | unplanned | Deployed frontend has been down since the sprint 4 dependency split |

## Tests

- Command: `/Users/hazra/Documents/Google_Hackathon/hotspot-sentinels/.venv/bin/python3 -m pytest tests -o addopts= --cov-config=/Users/hazra/Documents/Google_Hackathon/hotspot-sentinels/tests/coverage.ini --cov=backend --cov-report=term-missing --cov-report=json:/Users/hazra/Documents/Google_Hackathon/hotspot-sentinels/coverage.json -q --junit-xml=.pytest-report.xml`
- Result: **PASS**
- Summary: `667 passed, 3 warnings in 71.97s (0:01:11)`

## Coverage

- Configuration: `tests/coverage.ini` (backend application code)
- Total: **98.2%**

| File | Covered |
|------|---------|
| backend/main.py | 96.3% |
| backend/services/__init__.py | 100.0% |
| backend/services/alert_dispatcher.py | 100.0% |
| backend/services/database.py | 100.0% |
| backend/services/vision_analyzer.py | 100.0% |
| backend/tools/__init__.py | 100.0% |
| backend/tools/climate_service.py | 95.2% |
| backend/tools/maps_imagery_service.py | 97.9% |
| backend/tools/seed_samples.py | 98.9% |
| backend/verify_setup.py | 100.0% |
