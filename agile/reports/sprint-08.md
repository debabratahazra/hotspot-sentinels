# Sprint 8 Report

Generated 2026-10-04T13:05:36+00:00
Goal: Every change to the public repository is automatically tested, coverage-gated, secret-scanned, and proven to build both Cloud Run images

## Delivery

- Committed: 4 item(s)
- Completed: 4
- Carried over: 0
- Open bugs: 0

| Item | Type | Priority | Status | Title |
|------|------|----------|--------|-------|
| STORY-038 | story | P2 | done | As a contributor I can see test and coverage results for every change |
| STORY-039 | story | P2 | done | As a maintainer I can detect stale dependency exports before merge |
| STORY-040 | story | P2 | done | As an operator I can see both production images build for Cloud Run |
| STORY-041 | story | P2 | done | As a maintainer I can catch exposed credentials before code is merged |

## Tests

- Command: `/Users/hazra/Documents/Google_Hackathon/hotspot-sentinels/.venv/bin/python3 -m pytest tests -o addopts= --cov-config=/Users/hazra/Documents/Google_Hackathon/hotspot-sentinels/tests/coverage.ini --cov=backend --cov-report=term-missing --cov-report=json:/Users/hazra/Documents/Google_Hackathon/hotspot-sentinels/coverage.json -q --junit-xml=.pytest-report.xml`
- Result: **PASS**
- Summary: `656 passed, 3 warnings in 72.18s (0:01:12)`

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
