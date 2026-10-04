# Sprint 5 Planning

Phases 3 and 4 only, 2026-10-03. Phase 5 has not started.

## Decision table

States below show baseline -> grooming -> planning where applicable. All ten committed items are now in_sprint. No item was marked done, cancelled or newly created.

| Item      | Old state  | New state                | Why                                                                                                                                                                               |
| --------- | ---------- | ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| STORY-026 | blocked/P2 | ready/P1 -> in_sprint/P1 | Highest-value competition setup documentation; OQ-4 and another live deployment are not prerequisites.                                                                            |
| STORY-027 | blocked/P2 | ready/P1 -> in_sprint/P1 | Diagram the delivered flow; neither OQ-4 nor unbuilt GCS retention is required.                                                                                                   |
| STORY-030 | blocked/P1 | ready/P1 -> in_sprint/P1 | Additive caller provenance precedent makes the existing requirement groomable; exact representation agreement is the first handoff check, not a field shape invented by planning. |
| STORY-029 | blocked/P1 | ready/P2 -> in_sprint/P2 | Same-sprint dependency on STORY-030; P2 ensures prerequisite-first CLI selection and reflects a refinement of an already functional API.                                          |
| STORY-032 | blocked/P2 | ready/P2 -> in_sprint/P2 | Pure client documentation, sequenced after STORY-029; no OQ-4 dependency. Reconcile stale WebP criterion to JPEG/PNG.                                                             |
| TASK-020  | groomed/P1 | ready/P1 -> in_sprint/P1 | Workable sprint-4 process action: epic/dependency and structural-test checks.                                                                                                     |
| TASK-023  | groomed/P1 | ready/P1 -> in_sprint/P1 | Workable sprint-4 process action: one dispatch per item and complete write claims.                                                                                                |
| TASK-037  | ready/P1   | in_sprint/P1             | Fourth documentation-drift recurrence; correct the missed Docker instruction surface with offline regression evidence.                                                            |
| TASK-005  | blocked/P2 | ready/P2 -> in_sprint/P2 | Reporting is not blocked by full closure of broad QA stories; separate metrics/deltas and targeted follow-up remain unfinished.                                                   |
| TASK-039  | ready/P2   | in_sprint/P2             | Observed mobile clipping still needs bounded offline reproduction/repair, not assumed defect closure.                                                                             |
| STORY-022 | groomed/P2 | blocked/P2               | Offline suite is substantially met, but manual-script retirement requires TASK-038 human deletion approval.                                                                       |
| STORY-023 | blocked/P2 | groomed/P2               | Literal criteria appear already satisfied; remove unrelated retirement/future-provenance blockers and seek QA-backed human closure, not duplicate implementation.                 |
| STORY-025 | blocked/P2 | groomed/P2               | Literal canonical-contract criteria appear already satisfied; seek QA-backed human closure, not duplicate implementation.                                                         |
| STORY-031 | groomed/P2 | blocked/P2               | Real GCS storage/retrieval acceptance cannot be demonstrated under the standing no-cloud constraint.                                                                              |

Descriptions were also reconciled, without state/priority changes, for EPIC-009, STORY-024, STORY-028, TASK-006 and TASK-031. File claims were completed for STORY-030, STORY-029, STORY-032, TASK-020, TASK-023, TASK-037, TASK-005 and TASK-039. All nine epic containers remain groomed. Existing epic roll-up estimates above eight are not executable story estimates and are not split into invented scope.

## EPIC-009 split and stale blockers

Keep the existing epic, with two delivery lanes rather than creating new stories or epics:

- Documentation: STORY-026 and STORY-027 are independently workable; STORY-032 follows the same-sprint identity API delivery. No OQ-4 answer or cloud spend is needed.
- Competition rehearsal/submission: STORY-028 and TASK-006 remain blocked by recording-duration/submission constraints and their genuine unresolved prerequisites. TASK-031 remains blocked for the human OQ-4 answer.

Cleared stale blockers:

- STORY-026: remove OQ-4 and a new STORY-015 deployment requirement. Document existing sprint-3 deployment evidence and sprint-4 local-container evidence without claiming new live verification.
- STORY-027: remove OQ-4 and STORY-031. An architecture diagram describes implemented behavior and explicitly distinguishes deferred imagery retention.
- STORY-030: replace indefinite representation blocking with an explicit first handoff agreement checkpoint, grounded in the existing climate_source: caller precedent. No exact field names or representation are ratified here. If agreement fails, block the implementation and downstream identity/documentation dispatch.
- STORY-029 and STORY-032: selected earlier-in-sprint prerequisites are sequencing, not external blockers. Remove OQ-4 from STORY-032.
- STORY-023 and STORY-025: manual-script retirement and future identity extensions do not invalidate their already-delivered literal criteria.
- STORY-024: offline infrastructure already exists; remove STORY-022 retirement as a prerequisite. Retain the genuinely unmet STORY-029 caller-identity 422/boundary criterion.
- TASK-005: broad QA story closure is not required to improve an existing report generator. Reporting/tests remain offline and use the standing harness.
- STORY-028: STORY-017 is done, not partial; STORY-026 is now sequenced. OQ-4 and genuine unresolved rollback acceptance remain blockers.
- TASK-006: STORY-026/027 and TASK-005 are selected, not external blockers. OQ-4 and the rehearsal/rollback prerequisites remain unresolved.

Every baseline blocked item was reviewed. TASK-004/015, STORY-015/016 retain genuine live-evidence/quota blockers; TASK-011 retains protected-document human ownership; TASK-022 retains editor-policy approval; TASK-038 retains deletion approval. A deployed service does not prove the specific unfinished IAM, artifact-tagging, provisioning, bucket-upload or rollback criteria.

## EPIC-008 evidence assessment

No done transitions were made. These are criterion-level recommendations, not a fresh phase-6 execution or closure certification.

| Item      | Assessment                                               | Existing evidence / remaining criterion                                                                                                                                                                                                                                                                                                                                                                                     |
| --------- | -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| STORY-022 | Substantially met, not complete                          | pyproject.toml collects tests/ from the repository root. tests/conftest.py has autouse credential clearing, denied socket connections and denied real GenAI/Storage/Firestore/PubSub/BigQuery client construction, shared image bytes and mocked service/API fixtures. Sprint 4 reports 502 passing tests. backend/test_analyzer.py still exists; retirement AC is unmet and TASK-038 remains approval-blocked.             |
| STORY-023 | Literal AC appear met; recommend human QA-backed closure | tests/test_vision_analyzer.py, test_climate_service.py, test_alert_dispatcher.py and test_database.py assert success/failure paths; analyzer risk-band tests include 4.0/6.0/8.0. The shared harness forbids cloud calls. Sprint-4 coverage: analyzer/alerts/database 100%, climate 95.2%. Do not repeat a five-point suite expansion. STORY-030 owns its new provenance regressions.                                       |
| STORY-024 | Mostly met; not yet complete                             | tests/test_api.py covers 200, 415, 413, 502, 503 and safe error envelopes. It also tests legacy history and temperature 422s. Temperature rejection is not caller-identity rejection: main.py still accepts only image/temperature, so identity 422 and inclusive coordinate boundaries remain for STORY-029. Seek closure after that item's QA evidence instead of repeating broad API work.                               |
| STORY-025 | Literal AC appear met; recommend human QA-backed closure | tests/test_contract.py validates actual analyzer/database reports against the canonical schema and rejects malformed/non-UTC timestamps. tests/test_cross_layer_contract.py adds schema-field, coroutine, alert and UI contract regression guards. STORY-030 must update schema, validator and consumers together for the additive contract.                                                                                |
| TASK-005  | Substantially met, remaining work committed              | sprint_report.py already emits per-file coverage and below-70 flags; sprint-04.md supplies the delta, denominator explanation and separate 83.3% frontend/78.7% validator figures. The generator itself does not yet consistently automate all those additions or follow-up routing. Commit explicit separate metrics/deltas, denominator explanations and targeted branch evidence, not a redundant backend coverage push. |

Baseline backend coverage is 98.3%; no measured backend file is below 70%. Frontend/validator are separate denominators and also exceed the floor. No new test results are claimed by this planning session.

## Capacity and ready queue

Sprint 4 was accepted: 12/12 items, 19 completed points, zero carry-over, zero open bugs. Use completed velocity 19, not its unused 21-point ceiling. Sprint 5 commits 18/19 points; one point stays unallocated, not padded with unrelated debt and not permission for emergency additions without an explicit equal-size swap/rebaseline.

Allocation: documentation 6; identity 5; recurring process/instruction corrections 3; coverage-report follow-up 2; responsive verification 2. All documentation candidates fit. Optional evidence/mobile work does not displace competition documentation.

Verified pre-plan queue, sorted exactly by (priority, created):

| Order | Item      | Priority | Points |
| ----- | --------- | -------- | ------ |
| 1     | STORY-026 | P1       | 2      |
| 2     | STORY-027 | P1       | 2      |
| 3     | STORY-030 | P1       | 2      |
| 4     | TASK-020  | P1       | 1      |
| 5     | TASK-023  | P1       | 1      |
| 6     | TASK-037  | P1       | 1      |
| 7     | TASK-005  | P2       | 2      |
| 8     | STORY-029 | P2       | 3      |
| 9     | STORY-032 | P2       | 2      |
| 10    | TASK-039  | P2       | 2      |

Focused jq checks passed before and after planning: no new items, all nine epics groomed, no ready epic, complete AC/parent and executable estimate <=8, 18 points, 69 done items unchanged, no protected-document write claims, all committed items in_sprint and all named prerequisites done or selected earlier. Ready queue is now empty because all ten items were committed.

## Sprint goal and exact plan output

Goal: A judge can understand and run the delivered system and send a documented caller-identity analysis request with explicit provenance, supported by truthful offline quality evidence and no cloud spend.

```bash
bl plan --capacity 19 --goal 'A judge can understand and run the delivered system and send a documented caller-identity analysis request with explicit provenance, supported by truthful offline quality evidence and no cloud spend.'
```

Exact CLI output below, with terminal soft wrapping removed:

```text
Sprint 5 planned — 10 item(s), 18/19 points
  STORY-026  P1 (2) As a judge I can understand and run the project from the README alone
  STORY-027  P1 (2) As a judge I can see how the system fits together
  STORY-030  P1 (2) As an analyst I can tell a supplied zone identity apart from an inferred one
  TASK-020   P1 (1) Check epic containers and dependency sequencing before sprint planning
  TASK-023   P1 (1) Budget one Story Builder invocation per executable item
  TASK-037   P1 (1) docker-cloudrun instructions still prescribe a repository-root build context
  TASK-005   P2 (2) Produce a per-sprint coverage report with a 70% floor
  STORY-029  P2 (3) As an API client I can supply the zone identity with my upload and have it validated
  STORY-032  P2 (2) As an API client I can read one document that tells me exactly what to send
  TASK-039   P2 (2) Verify and resolve dashboard clipping with the expanded mobile sidebar
```

## File-grouped build order

Arrows mean serialize these item writers in this order. Separate test files are separate claims; sharing tests/ alone is not a conflict. One subagent must never overwrite an earlier item's changes.

| Claimed file or output                                                        | Item write order                                                          |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| .github/skills/agile-sdlc-loop/references/phases.md                           | TASK-020 -> TASK-023                                                      |
| agile/reports/sprint-05-planning.md                                           | TASK-020 -> TASK-023                                                      |
| .github/instructions/docker-cloudrun.instructions.md                          | TASK-037                                                                  |
| tests/test_sprint_packaging.py                                                | TASK-037 (offline consistency regression only)                            |
| README.md                                                                     | STORY-026 -> STORY-027 -> STORY-032                                       |
| docs/api-input-guide.md                                                       | STORY-032                                                                 |
| backend/services/vision_analyzer.py                                           | STORY-030                                                                 |
| backend/main.py                                                               | STORY-030 (response/legacy contract only) -> STORY-029 (multipart route)  |
| frontend/app.py                                                               | STORY-030 (contract consumer only) -> TASK-039                            |
| COPILOT_GUIDE.md                                                              | STORY-030                                                                 |
| .github/skills/heat-report-validation/assets/heat_analysis_result.schema.json | STORY-030                                                                 |
| .github/skills/heat-report-validation/scripts/validate_report.py              | STORY-030 -> TASK-005 (targeted branch follow-up only)                    |
| tests/conftest.py                                                             | STORY-030 (shared contract fixture)                                       |
| tests/test_vision_analyzer.py                                                 | STORY-030                                                                 |
| tests/test_api.py                                                             | STORY-030 -> STORY-029                                                    |
| tests/test_cross_layer_contract.py                                            | STORY-030 -> STORY-029                                                    |
| tests/test_contract.py                                                        | STORY-030 -> STORY-029 -> TASK-005                                        |
| tests/test_frontend.py                                                        | STORY-030 -> TASK-039 -> TASK-005                                         |
| .github/skills/agile-sdlc-loop/scripts/sprint_report.py                       | TASK-005                                                                  |
| tests/test_sprint_report.py                                                   | TASK-005                                                                  |
| tests/coverage.ini                                                            | TASK-005                                                                  |
| agile/reports/sprint-05.md                                                    | TASK-005 reporting/evidence output, not a planning-time completion report |
| agile/reports/sprint-05-mobile/                                               | TASK-039 viewport screenshots/evidence                                    |

No dependency manifests change, so pyproject.toml, uv.lock and either requirements export need no write claim. If a dependency change becomes necessary, stop and update scope/claims/estimates first; do not repeat the TASK-032 lockfile omission.

Known structural-test impact is included in existing item estimates: STORY-030/029 affect schema assumptions and envelope allowlists in tests/test_contract.py and tests/test_cross_layer_contract.py, legacy API models/fixtures in tests/test_api.py, and frontend mocked-report assumptions in tests/test_frontend.py. TASK-039 affects frontend element/label/layout assertions, not feature semantics. TASK-005 affects denominator/report-output assertions in tests/test_sprint_report.py. TASK-037 adds a static context check without changing packaging or foundation expectations. tests/test_foundation.py and tests/test_package_layout.py need no planned writes: dependency/import/runtime layout remains unchanged; treat failures there by reconciling the owning acceptance criterion before expanding scope.

## Wave plan

Each named item gets one separate Story Builder invocation (10 total); TASK-039 can route that single item invocation to dashboard-designer under the orchestrator's existing routing convention. No invocation is started here. Each handoff is checked before the next dependent dispatch. QA/contract audits are independent later invocations, not hidden implementation points.

| Wave | Safe dispatch                                              | Dependency / conflict rule                                                                                                                                                                                                |
| ---- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0    | TASK-020, then TASK-023; TASK-037 may run alongside either | Process tasks share phases.md and this planning record, so serialize them. TASK-037 files are disjoint. Complete pre-dispatch/write-claim checks before product waves.                                                    |
| 1    | STORY-026 in parallel with STORY-030                       | README and identity claims are disjoint. Before STORY-030 code, product-owner/contract-auditor agree exact serialized provenance and legacy behavior. Failed agreement blocks downstream work; no fabricated field names. |
| 2    | STORY-027 in parallel with STORY-029                       | Both follow their wave-1 predecessors. README and API/contract-test claims are disjoint. STORY-030 must finish its complete schema/consumer slice before STORY-029 starts.                                                |
| 3    | STORY-032 in parallel with TASK-039                        | Client guide follows demonstrated STORY-029 and links README after STORY-027. Mobile task follows STORY-030 consumer changes; guide and frontend claims are disjoint.                                                     |
| 4    | TASK-005 alone                                             | Wait for identity, API and mobile writers to release shared validator, frontend and contract-test files before collecting final coverage evidence.                                                                        |

Budget ten item dispatches plus ten checked handoffs, four wave barriers and one pre-identity contract-agreement checkpoint as orchestration overhead, separately from the 18 implementation points. No extra product scope is hidden in that count.

Offline validation requirements for later agents: mocked clients and no external network; focused tests before broader checks; schema/legacy and cross-layer gates for identity; static context consistency for TASK-037; viewport screenshots with mocked requests for TASK-039; separately accounted backend/frontend/validator coverage for TASK-005. Do not execute the packaging suite indiscriminately in this planning session because some tests invoke Docker.

Local container smoke remains the accepted deployability method: docker build -f backend/Dockerfile backend, run without network/credentials, exercise /api/live, /api/health and rejection paths when that later validation phase is explicitly authorized. No redeploy or live Gemini, BigQuery, Firestore, Pub/Sub or GCS is planned. No gcloud or docker command was run in phases 3-4.

## Deferred items

| Item(s)                                  | Reason / next disposition                                                                                                                                                                                                                                                                                          |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| TASK-031                                 | Human OQ-4 deadline, recording-duration and form/sharing answers still absent.                                                                                                                                                                                                                                     |
| STORY-028, TASK-006                      | Genuine OQ-4-dependent rehearsal/submission; protected runbook scope also requires authorized relocation/human ownership.                                                                                                                                                                                          |
| TASK-038, STORY-022                      | Deletion approval not given; manual-script retirement remains unfinished.                                                                                                                                                                                                                                          |
| TASK-004, TASK-015, STORY-015, STORY-016 | Specific IAM/provisioning/GCS/Artifact Registry/rollback live criteria remain unproven and quota-prohibited. Existing sprint-3 deployment is not a reason to redo it or to claim every deferred criterion met.                                                                                                     |
| STORY-031                                | Actual retained-image/heatmap GCS retrieval acceptance prohibited by no-cloud rule.                                                                                                                                                                                                                                |
| STORY-023, STORY-025                     | Already-met literal criteria appear closure candidates; human QA-backed disposition, not a redundant build assignment.                                                                                                                                                                                             |
| STORY-024                                | Existing status/error coverage substantially met; final identity-422 criterion belongs to STORY-029 tests, then seek closure.                                                                                                                                                                                      |
| STORY-014                                | Sprint-4 local container evidence and packaging tests substantially cover it; seek owning QA reconciliation of exact base-image/no-credentials criteria rather than duplicate a three-point build. Its .dockerignore claim is stale versus backend/.dockerignore and must be corrected before any future dispatch. |
| TASK-011                                 | Human-only protected foundation docs update.                                                                                                                                                                                                                                                                       |
| TASK-022                                 | Human-approved editor/template-access policy remains unresolved; no bypass.                                                                                                                                                                                                                                        |
| TASK-014, TASK-019                       | Lower-value environment override/process follow-up stays groomed and uncommitted; do not pad the remaining point. TASK-019's existing coordinate/isolation evidence should be reused if later prioritized.                                                                                                         |

## Final bl stats

```json
{
  "current_sprint": 5,
  "total": 106,
  "open": 35,
  "open_bugs": 0,
  "by_status": {
    "groomed": 14,
    "in_sprint": 10,
    "done": 69,
    "blocked": 13
  },
  "by_type": {
    "epic": 9,
    "story": 33,
    "task": 39,
    "bug": 24,
    "test": 1
  },
  "loop_done": false
}
```

Single next action: authorize the orchestrator to begin Phase 5 with wave 0 and its separate item dispatches. This session stops after planning.
