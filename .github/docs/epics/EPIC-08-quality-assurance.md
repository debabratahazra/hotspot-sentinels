# EPIC-08 — Quality Assurance & Test Coverage

|                |                                                                                                                                   |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Goal**       | Every acceptance criterion in every epic is proven by a test that runs with no credentials and no network.                        |
| **Source**     | Implied by the coverage reporting in [agile-sdlc-loop](../../skills/agile-sdlc-loop/SKILL.md); not scoped in the original backlog |
| **Priority**   | P1                                                                                                                                |
| **Status**     | Not started                                                                                                                       |
| **Depends on** | runs alongside EPIC-02 through EPIC-07                                                                                            |
| **Delivers**   | `tests/`, `agile/reports/sprint-NN.md`                                                                                            |

## Why this epic exists

The original backlog had no testing epic at all — it proposed verifying each story by running `python backend/main.py` by hand. That does not scale past the third module and cannot produce the coverage report the sprint workflow requires.

The existing `backend/test_analyzer.py` shows the problem: it is named like a test but is an ad-hoc script that calls live Vertex AI, costs money on every run, cannot assert anything, lives outside `tests/`, and currently fails because `from services.vision_analyzer` does not resolve when invoked from the repository root.

This epic is **not** a final phase. Tests are written in the same sprint as the code they cover.

## Scope

**In:** pytest harness, fixtures, mocking strategy, unit and route tests, contract conformance, coverage measurement and reporting.

**Out:** live integration against real cloud services — that is the `pipeline-smoke-test` skill, run manually before a deploy or demo.

## Non-negotiable rule

No test calls Google Cloud. No Vertex AI, no Firestore write, no Pub/Sub publish, no BigQuery job. Mock at the client boundary. A test that needs credentials is a broken test.

## Stories

### Story 8.1 — Test harness and fixtures
- **Files:** `tests/conftest.py`, `pytest.ini` or `pyproject.toml`
- **Estimate:** 3 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] `pytest tests` runs from the repository root with `backend/` importable
  - [ ] Shared fixtures: fake genai client, fake Firestore, fake publisher, in-memory PNG bytes, a valid report payload
  - [ ] Image fixtures generated with Pillow at a few hundred bytes — no committed binaries
  - [ ] The suite passes with `GOOGLE_APPLICATION_CREDENTIALS` unset and no network
  - [ ] `backend/test_analyzer.py` retired or converted into a proper test

### Story 8.2 — Service-layer unit tests
- **Files:** `tests/test_vision_analyzer.py`, `tests/test_climate_service.py`, `tests/test_alert_dispatcher.py`, `tests/test_database.py`
- **Estimate:** 5 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**

  | Module             | Must assert                                                                                                               |
  | ------------------ | ------------------------------------------------------------------------------------------------------------------------- |
  | `vision_analyzer`  | schema-valid dict; `VisionAnalysisError` on malformed JSON and SDK failure; image bytes never logged                      |
  | `climate_service`  | °F→°C conversion; `9999.9` sentinel filtered; fallback 35–41 °C with `source="fallback"`; station id bound as a parameter |
  | `alert_dispatcher` | publishes at HVI ≥ 8.0; returns `""` below with no client call; publish failure returns `""` without raising              |
  | `database`         | save/read round trip; `limit` clamped; timestamps serialisable; `DatabaseError` on failure                                |

  - [ ] Boundary cases are mandatory: HVI exactly 4.0, 6.0 and 8.0; percentages totalling 100; empty scans list

### Story 8.3 — API route tests
- **File:** `tests/test_api.py`
- **Estimate:** 3 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Uses `fastapi.testclient.TestClient` with all services mocked
  - [ ] Asserts 200 health, 415 wrong content type, 413 oversized upload, 502 on `VisionAnalysisError`, 503 on `DatabaseError`
  - [ ] Asserts responses leak no stack trace, project ID, bucket name, or topic path
  - [ ] Asserts an empty scans collection returns `[]` with 200

### Story 8.4 — Contract conformance tests
- **File:** `tests/test_contract.py`
- **Estimate:** 2 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Representative payloads validated against `heat_analysis_result.schema.json`
  - [ ] `risk_level` asserted against `hvi_score` at every band boundary
  - [ ] `alert_dispatched` asserted never true below 8.0
  - [ ] A deliberately malformed payload is asserted to fail validation — proving the validator works

### Story 8.5 — Coverage reporting
- **Files:** `agile/reports/sprint-NN.md`
- **Estimate:** 2 · **Priority:** P2 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] `python3 .github/skills/agile-sdlc-loop/scripts/sprint_report.py` produces the report with per-file coverage
  - [ ] Total coverage and the delta from the previous sprint are reported
  - [ ] Any touched file below 70% generates a test task in the backlog
  - [ ] The report is written every sprint, including sprints where coverage fell

## Definition of done

`pytest tests` is green with no credentials, every acceptance criterion across EPIC-02 to EPIC-07 maps to at least one test, total coverage is at or above 70%, and the sprint report records it.

## Risks

| Risk                                       | Mitigation                                                       |
| ------------------------------------------ | ---------------------------------------------------------------- |
| Tests quietly calling live cloud services  | Mock at the client boundary; CI-style run with credentials unset |
| Production code bent to make a test pass   | QA files a bug instead; the `qa-engineer` agent forbids it       |
| Assertions weakened to go green            | `pytest.skip` with a reason, or fix the cause                    |
| Coverage gamed by tests without assertions | Review that each test maps to a named acceptance criterion       |
| Tests deferred to a final sprint           | This epic runs alongside 02–07, not after                        |

## Seed the backlog

```bash
bl() { python3 .github/skills/agile-sdlc-loop/scripts/backlog.py "$@"; }
bl add --type epic --title "Quality Assurance and Test Coverage" --priority P1 \
  --description "Credential-free pytest suite proving every acceptance criterion, plus coverage reporting"
bl add --type story --parent EPIC-008 --priority P1 --estimate 3 --source qa \
  --title "As a developer I can run the whole suite offline with one command" \
  --files tests/conftest.py \
  --ac "pytest tests runs from the repo root" "passes with credentials unset and no network" \
       "shared fixtures for genai, Firestore, Pub/Sub and image bytes" "backend/test_analyzer.py retired"
bl add --type story --parent EPIC-008 --priority P1 --estimate 5 --source qa \
  --title "As a developer every service module is covered by mocked unit tests" \
  --ac "each module asserts its success and failure paths" "HVI boundaries 4.0, 6.0 and 8.0 tested" \
       "no test calls a real cloud service"
bl add --type story --parent EPIC-008 --priority P1 --estimate 3 --source qa \
  --title "As a developer every API status code is covered" \
  --files tests/test_api.py \
  --ac "200, 415, 413, 502 and 503 asserted" "responses asserted free of internal detail"
bl add --type story --parent EPIC-008 --priority P1 --estimate 2 --source qa \
  --title "As an auditor the payload contract is enforced by tests" \
  --files tests/test_contract.py \
  --ac "payloads validated against the canonical schema" "a malformed payload is asserted to fail"
bl add --type task --parent EPIC-008 --priority P2 --estimate 2 --source qa \
  --title "Produce a per-sprint coverage report with a 70% floor" \
  --ac "sprint report includes per-file coverage and the delta" "files below 70% generate test tasks"
```
