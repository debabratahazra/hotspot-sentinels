# Sprint 1 Report

Generated 2026-10-02T10:51:32+00:00
Goal: Complete the foundation so an analyst can score a zone from an aerial image end to end through Gemini analysis using synthetic sample scenes.

## Delivery

- Committed: 9 item(s)
- Completed: 9
- Carried over: 0
- Open bugs: 1

| Item      | Type  | Priority | Status | Title                                                               |
| --------- | ----- | -------- | ------ | ------------------------------------------------------------------- |
| TASK-001  | task  | P1       | done   | Initialise the git repository so .gitignore takes effect            |
| TASK-002  | task  | P1       | done   | Make verify_setup.py read project, region and model from env vars   |
| TASK-003  | task  | P1       | done   | Create the backend/tools package                                    |
| STORY-001 | story | P2       | done   | As an analyst I can score a zone from an aerial image               |
| STORY-002 | story | P2       | done   | As a developer I have three synthetic aerial scenes to test against |
| TASK-007  | task  | P1       | done   | Complete setup configuration and correct the provisioning command   |
| TASK-008  | task  | P1       | done   | Provide a secret-free environment template for new developers       |
| TASK-009  | task  | P1       | done   | Settle and document the backend test import strategy                |
| TASK-010  | task  | P1       | done   | Align Python support and dependencies using pyproject.toml and uv   |

## Tests

- Result: **PASS**
- Summary: `---------------------------------------
TOTAL                                    329    126    62%
Coverage JSON written to file /Users/hazra/Documents/Google_Hackathon/hotspot-sentinels/coverage.json`

## Coverage

- Total: **61.7%**

| File                                 | Covered |
| ------------------------------------ | ------- |
| backend/main.py                      | 0.0%    |
| backend/services/__init__.py         | 100.0%  |
| backend/services/alert_dispatcher.py | 0.0%    |
| backend/services/database.py         | 0.0%    |
| backend/services/vision_analyzer.py  | 100.0%  |
| backend/test_analyzer.py             | 0.0%    |
| backend/test_pipeline.py             | 0.0%    |
| backend/tools/__init__.py            | 100.0%  |
| backend/tools/climate_service.py     | 0.0%    |
| backend/tools/seed_samples.py        | 98.9%   |
| backend/verify_setup.py              | 100.0%  |

Below the 70% floor — needs test tasks next sprint:
- backend/main.py
- backend/services/alert_dispatcher.py
- backend/services/database.py
- backend/test_analyzer.py
- backend/test_pipeline.py
- backend/tools/climate_service.py

## Open bugs carried forward

- BUG-006 (P1) Report validator accepts timezone-naive and non-UTC timestamps

## Retrospective

Sprint closed with 9/9 committed items done, 15/15 points delivered, and zero carry-over. The supplied sprint evidence records 82 passing tests. The goal was met at the code level; live cloud acceptance remains undemonstrated under TASK-015, and deployment remains blocked under TASK-013. Phase 11 sign-off was not run.

Retain these practices:
- Sprint-touched modules exceeded 98% coverage: vision_analyzer and verify_setup at 100%, seed_samples at 98.9%.
- Keep independent Phase 8 contract auditing: it caught BUG-005, a BLOCKER missed by all 82 passing tests.
- Keep the red-build rule: Phase 6 caught four P0 defects before deploy.
- Keep the settled backend pythonpath and the two static import/layering checks.

| Finding                                                                             | Follow-up                                                                                    |
| ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| BUG-004: verified a temporary lockfile rather than the untouched workspace artefact | TASK-016: verify canonical generated artefacts in place                                      |
| BUG-005: narrowed CLOUD_ERRORS, silently dropping DataCorruption without a test     | TASK-017: require same-change regression tests for narrowed exception or validation coverage |
| BUG-003: omitted required documentation; README remained empty                      | TASK-018: verify every acceptance criterion, including documentation                         |
| BUG-001: caller coordinates bypassed validation and were aliased                    | TASK-019: require override validation and mutation-isolation checks                          |
| Grooming made epic containers ready and falsely blocked same-sprint prerequisites   | TASK-020: pre-plan container and dependency checks                                           |
| Test name was dynamically hidden solely to evade grep                               | TASK-021: reject verification evasion and require discoverable tests                         |
| Editor ignored the approved .env.example template, blocking TASK-012                | TASK-022: align safe template access and secret protection                                   |
| Whole-backend coverage is 61.7%, below NFR-9                                        | TEST-001: existing coverage follow-up                                                        |
| Provisioning, GCS uploads, and authenticated Vertex AI criteria are asserted-only   | TASK-015: existing live-validation follow-up                                                 |
| Phase 7 deployment was skipped by human decision                                    | TASK-013: existing blocked deployment follow-up                                              |
| Eight single-item Story Builder delegations were not anticipated                    | TASK-023: budget per-item invocations and orchestration overhead                             |

Existing audit follow-ups BUG-006 (UTC timestamp validation) and TASK-014 (overridable Pub/Sub topic configuration) were retained without duplication. All eight new tasks and five existing follow-ups carry source=retro; original QA/validation provenance remains in the existing descriptions. No item was marked done.
