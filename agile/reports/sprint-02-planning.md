# Sprint 2: Grooming and Planning

## Decision table

States below include priority. This table records every grooming status or priority change. The separate commitment table records every planning transition. No item was marked done.

| Item      | Old state  | Groomed state | Why                                                                                                                                      |
| --------- | ---------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| STORY-004 | blocked/P1 | ready/P1      | Foundation shipped; BUG-010 is committed first; complete FR-8 telemetry slice.                                                           |
| STORY-005 | blocked/P1 | ready/P2      | STORY-004 is committed; same-sprint sequencing, not a blocker; broader fallback acceptance is lower priority.                            |
| STORY-006 | blocked/P1 | ready/P1      | Foundation shipped; complete persistence and bounded history prerequisite.                                                               |
| STORY-007 | blocked/P1 | ready/P1      | Foundation shipped; publisher slice is workable but cannot fit this sprint.                                                              |
| STORY-008 | blocked/P1 | blocked/P2    | Depends on uncommitted STORY-007; cannot outrank service prerequisites.                                                                  |
| STORY-009 | blocked/P1 | blocked/P2    | STORY-005/007 uncommitted and OQ-5 unresolved; downstream readiness work.                                                                |
| STORY-010 | blocked/P1 | blocked/P2    | Full controller dependencies and OQ-2 unresolved; not a prerequisite for narrow P0 repairs.                                              |
| STORY-012 | blocked/P1 | ready/P2      | Analyzer shipped and STORY-006 committed; error-mapping work is sequenced after its prerequisites.                                       |
| STORY-013 | blocked/P1 | ready/P2      | STORY-006 committed; API history slice is same-sprint sequencing, not a blocker.                                                         |
| STORY-014 | blocked/P1 | blocked/P2    | Full image acceptance awaits API work and TASK-025; unrelated dashboard dependencies removed.                                            |
| STORY-015 | blocked/P1 | blocked/P2    | Depends on image acceptance and runtime IAM; deployment follows prerequisites.                                                           |
| TASK-004  | blocked/P1 | ready/P2      | TASK-007 shipped; narrow runtime IAM work is executable but lower priority than pipeline repair.                                         |
| STORY-016 | blocked/P1 | blocked/P2    | Verified deployment and full analysis remain uncommitted.                                                                                |
| STORY-017 | blocked/P1 | blocked/P2    | Full API/history/identity prerequisites uncommitted; dashboard work follows backend.                                                     |
| STORY-018 | blocked/P1 | blocked/P2    | Dashboard controls and paired HVI evidence uncommitted.                                                                                  |
| STORY-019 | blocked/P1 | blocked/P2    | Analyzer shipped; dashboard controls still uncommitted.                                                                                  |
| STORY-020 | blocked/P1 | blocked/P2    | Dashboard and full stored dispatch-provenance prerequisites uncommitted.                                                                 |
| STORY-021 | blocked/P1 | blocked/P2    | Dashboard prerequisite uncommitted and OQ-5 timeout limits unresolved.                                                                   |
| STORY-022 | blocked/P1 | ready/P2      | Package-layout and dependency prerequisites shipped; broad offline-suite work deferred.                                                  |
| STORY-023 | blocked/P1 | blocked/P2    | Broad service-suite dependencies remain uncommitted.                                                                                     |
| STORY-024 | blocked/P1 | blocked/P2    | Full API-suite dependencies remain uncommitted.                                                                                          |
| STORY-025 | blocked/P1 | blocked/P2    | Offline-suite and identity-provenance prerequisites remain uncommitted.                                                                  |
| STORY-026 | blocked/P1 | blocked/P2    | Foundation shipped; verified deployment still uncommitted.                                                                               |
| STORY-029 | blocked/P1 | blocked/P2    | API identity work follows analyzer provenance STORY-030.                                                                                 |
| STORY-030 | blocked/P1 | blocked/P2    | Reverse STORY-029 dependency removed; serialized provenance contract still needs product-owner/contract-auditor agreement.               |
| BUG-006   | new/P1     | ready/P2      | Attach to EPIC-008, FR-24 and FR-3; validator timestamp gap is independently workable but does not repair live orchestration.            |
| BUG-007   | new/P0     | ready/P0      | Reproduced deployed coroutine failure; urgent narrow async repair.                                                                       |
| BUG-008   | new/P0     | ready/P0      | Reproduced deleted-field alert gate; follows BUG-007 and uses actual publisher outcome.                                                  |
| BUG-009   | new/P1     | ready/P1      | Environment/CORS prerequisite shipped; same controller file as urgent defects.                                                           |
| BUG-010   | new/P0     | ready/P0      | Reproduced SQL interpolation; security, sentinel and labelled-fallback repair precedes full climate slice.                               |
| BUG-011   | new/P0     | ready/P0      | Credential-packaging exposure; exclusions must govern actual build context.                                                              |
| BUG-012   | new/P0     | ready/P0      | Reproduced deleted dashboard fields; narrow rendering repair follows API defects.                                                        |
| BUG-013   | new/P1     | ready/P2      | Explicit configurable timeout, URL configuration and safe errors are workable; broader dashboard SLO remains OQ-5.                       |
| TASK-011  | new/P2     | blocked/P2    | Add criteria from existing defect description; human must edit protected documentation.                                                  |
| TASK-014  | new/P2     | ready/P2      | Attach EPIC-001/NFR-5 and add override/default criteria from existing scope; independently workable.                                     |
| TEST-001  | new/P2     | ready/P2      | Attach EPIC-008/FR-24/FR-25/NFR-9; coverage work can run against existing modules without artificial rewrite blockers.                   |
| TASK-015  | new/P1     | blocked/P2    | Attach EPIC-001/FR-1/FR-2/FR-7; human provisioning and approved live evidence remain unverified.                                         |
| TASK-016  | new/P1     | ready/P2      | Valid artifact-verification prevention, below working-pipeline scope.                                                                    |
| TASK-017  | new/P1     | ready/P2      | Valid regression-test prevention, below working-pipeline scope.                                                                          |
| TASK-018  | new/P1     | ready/P2      | Valid criterion-by-criterion handoff prevention, below working-pipeline scope.                                                           |
| TASK-019  | new/P1     | ready/P2      | Valid override-validation/ownership prevention, below working-pipeline scope.                                                            |
| TASK-020  | new/P1     | ready/P2      | Valid planning-guard prevention; checks performed now without claiming task completion.                                                  |
| TASK-021  | new/P1     | ready/P2      | Valid discoverable-test/verification-integrity prevention, below pipeline scope.                                                         |
| TASK-022  | new/P1     | blocked/P2    | Human approval required for safe template/editor policy; no ignore bypass.                                                               |
| TASK-023  | new/P2     | ready/P2      | Valid per-item delegation budgeting, below pipeline scope.                                                                               |
| TASK-024  | new/P1     | ready/P1      | Restore single authoritative dependency source; regenerate transitional backend export if needed rather than breaking its current build. |
| TASK-025  | new/P1     | ready/P2      | Docker hardening follows BUG-011/TASK-024; lower priority than climate and persistence slices.                                           |

| Item      | Pre-plan state | Planned state | Why                                                 |
| --------- | -------------- | ------------- | --------------------------------------------------- |
| BUG-007   | ready/P0       | in_sprint/P0  | 2 points; live analyze failure.                     |
| BUG-008   | ready/P0       | in_sprint/P0  | 1 point; alert gate repair.                         |
| BUG-010   | ready/P0       | in_sprint/P0  | 1 point; SQL injection repair.                      |
| BUG-011   | ready/P0       | in_sprint/P0  | 1 point; credential exclusions.                     |
| BUG-012   | ready/P0       | in_sprint/P0  | 2 points; visible schema repair.                    |
| STORY-004 | ready/P1       | in_sprint/P1  | 3 points; complete labelled, valid climate reading. |
| STORY-006 | ready/P1       | in_sprint/P1  | 3 points; complete persistence and history.         |
| BUG-009   | ready/P1       | in_sprint/P1  | 1 point; fits after larger STORY-007 is skipped.    |
| TASK-024  | ready/P1       | in_sprint/P1  | 1 point; tested dependency consistency.             |

## Evidence and reconciliation

- Read phases 3-4 first, the skill, requirements, project guide/backlog specification, relevant story documents, backlog criteria, CLI selection code, and controlling service/controller code.
- Actual starting state was 80 items, 22 new, 33 blocked, nine groomed epics, one ready story and 15 done items. Sprint 1 committed/completed nine items totaling 15 points; the 15 done backlog items also include QA fixes and pre-existing work outside that commitment.
- TASK-012 is already done according to QA evidence; it was not new and was not reopened. BUG-006 already has a one-point estimate. Eight unresolved bugs exist; the ninth listed new change is TASK-025, not another bug. No new items were invented.
- Every open executable now has acceptance criteria, a valid parent, a traceable FR/NFR and an estimate from 1, 2, 3, 5, 8. No executable estimate exceeds eight. Epic roll-ups above eight are not executable stories and remain groomed.
- Missing parents repaired: BUG-006 and TEST-001 to EPIC-008; TASK-014 and TASK-015 to EPIC-001. TASK-011/TASK-014 missing criteria were derived from their existing requested corrections, not new product scope.
- STORY-004, STORY-005, STORY-006 and STORY-030 criteria were reconciled with their story documents. In particular, STORY-005 no longer promises to hide programming defects behind an unconditional fallback.
- Overlapping defects and stories remain separate, not duplicate commitments: the documents explicitly retain separate estimates for narrow repairs and complete contract slices. STORY-004 adds full reading metadata/client behavior beyond BUG-010. Full publishing, stored-dispatch provenance, full API and full dashboard acceptance remain distinct.
- Protected story documentation, production code and tests were not edited. No development, deployment, live cloud validation, completion report, retrospective or sign-off was run.

## Stale blockers cleared

| Item      | Cleared blocker                                                             | Remaining sequencing                             |
| --------- | --------------------------------------------------------------------------- | ------------------------------------------------ |
| STORY-004 | TASK-002/007/008/009/010 all shipped                                        | BUG-010 committed before full telemetry work.    |
| STORY-006 | TASK-002/007/008/009/010 all shipped                                        | No unfinished prerequisite.                      |
| STORY-007 | TASK-002/007/008/009/010 all shipped                                        | Ready, deferred only by capacity.                |
| TASK-004  | TASK-007 shipped                                                            | Ready, deferred only by priority/capacity.       |
| STORY-022 | TASK-009/010 shipped                                                        | Ready, deferred only by priority/capacity.       |
| STORY-005 | Stale rule requiring STORY-004 already done                                 | STORY-004 is committed to this sprint; ready/P2. |
| STORY-012 | STORY-001 and TASK-007 shipped; stale rule requiring STORY-006 already done | STORY-006 is committed to this sprint; ready/P2. |
| STORY-013 | Stale rule requiring STORY-006 already done                                 | STORY-006 is committed to this sprint; ready/P2. |

All 33 initially blocked items were reevaluated. Completed dependencies were removed from blocker reasons even where other blockers remain. STORY-011 now names only its unresolved byte-limit decision rather than shipped foundation blockers. STORY-030 no longer depends on STORY-029; it remains blocked on the unagreed serialized provenance contract. STORY-014 no longer falsely depends on frontend completion. Eight stale blockers were cleared and three new human-owned blockers were recorded, leaving 28 genuinely blocked items.

## Verified ready queue before planning

Sorted by the actual CLI key `(priority, created)`; equal timestamps retain backlog order. All nine epics were verified groomed, never ready. The queue contained 28 executables totaling 44 points.

| Order | Item      | Priority | Points | CLI result              |
| ----- | --------- | -------- | ------ | ----------------------- |
| 1     | BUG-007   | P0       | 2      | Select                  |
| 2     | BUG-008   | P0       | 1      | Select                  |
| 3     | BUG-010   | P0       | 1      | Select                  |
| 4     | BUG-011   | P0       | 1      | Select                  |
| 5     | BUG-012   | P0       | 2      | Select                  |
| 6     | STORY-004 | P1       | 3      | Select                  |
| 7     | STORY-006 | P1       | 3      | Select                  |
| 8     | STORY-007 | P1       | 3      | Skip: 13 + 3 exceeds 15 |
| 9     | BUG-009   | P1       | 1      | Select                  |
| 10    | TASK-024  | P1       | 1      | Select                  |
| 11    | STORY-003 | P2       | 2      | Defer                   |
| 12    | STORY-005 | P2       | 2      | Defer                   |
| 13    | STORY-012 | P2       | 2      | Defer                   |
| 14    | STORY-013 | P2       | 1      | Defer                   |
| 15    | TASK-004  | P2       | 2      | Defer                   |
| 16    | STORY-022 | P2       | 3      | Defer                   |
| 17    | BUG-006   | P2       | 1      | Defer                   |
| 18    | TASK-014  | P2       | 1      | Defer                   |
| 19    | TEST-001  | P2       | 1      | Defer                   |
| 20    | TASK-016  | P2       | 1      | Defer                   |
| 21    | TASK-017  | P2       | 1      | Defer                   |
| 22    | TASK-018  | P2       | 1      | Defer                   |
| 23    | TASK-019  | P2       | 1      | Defer                   |
| 24    | TASK-020  | P2       | 1      | Defer                   |
| 25    | TASK-021  | P2       | 1      | Defer                   |
| 26    | TASK-023  | P2       | 1      | Defer                   |
| 27    | BUG-013   | P2       | 2      | Defer                   |
| 28    | TASK-025  | P2       | 2      | Defer                   |

## Sprint goal

An analyst can submit an aerial image, receive a valid heat report grounded in labelled climate data, review persisted scans, and see truthful critical-alert status without the current coroutine, schema, SQL-injection or credential-packaging failures.

## Exact plan output

Command: `python3 .github/skills/agile-sdlc-loop/scripts/backlog.py plan --capacity 15 --goal "<sprint goal above>"`

```text
Sprint 2 planned — 9 item(s), 15/15 points
  BUG-007    P0 (2) /api/analyze never awaits the async analyzer, returning a coroutine
  BUG-008    P0 (1) Critical alerts never fire because main.py reads a deleted schema field
  BUG-010    P0 (1) BigQuery climate query interpolates station_id into SQL
  BUG-011    P0 (1) No .dockerignore, so COPY . . can bake .env and .venv into the image
  BUG-012    P0 (2) Dashboard reads schema fields that no longer exist
  STORY-004  P1 (3) As an analyst my zone score is grounded in a real ambient temperature
  STORY-006  P1 (3) As an analyst I can see my previous scans
  BUG-009    P1 (1) CORS allows every origin instead of reading ALLOWED_ORIGINS
  TASK-024   P1 (1) Remove the duplicate backend/requirements.txt manifest
```

Arithmetic: five P0 defects = 7; CORS and manifest = 2; climate and persistence = 6; total = 15. No capacity stretch and no epic commitment.

## Dependency confirmation and Phase 5 handoff

Executable post-plan validation passed: every committed dependency is done or committed to sprint 2. No committed item depends on an uncommitted story. All nine committed executables are in_sprint; no in_progress/in_review transition occurred; done count remains 15.

| Committed item | Satisfied dependencies                           |
| -------------- | ------------------------------------------------ |
| BUG-007        | STORY-001, TASK-009 done                         |
| BUG-008        | BUG-007 committed                                |
| BUG-010        | TASK-002, TASK-009 done                          |
| BUG-011        | TASK-010 done                                    |
| BUG-012        | BUG-007, BUG-008 committed                       |
| STORY-004      | TASK-002/007/008/009/010 done; BUG-010 committed |
| STORY-006      | TASK-002/007/008/009/010 done                    |
| BUG-009        | TASK-007 done                                    |
| TASK-024       | TASK-010 done                                    |

Recommended build order, distinct from CLI selection order:

1. BUG-010: urgent query repair and explicit fallback/sentinel behavior.
2. BUG-007: immediately repair the deployed coroutine path, wrapping sync boundaries and adapting climate reading shapes without waiting for the full API story.
3. BUG-008: repair critical gating and real publish-outcome handling while the controller is open.
4. BUG-009: configure CORS in the same controller work sequence.
5. BUG-011: effective credential exclusions for the build context actually used; verify startup and image contents without claiming full Docker hardening.
6. TASK-024: restore dependency consistency, preserving a generated transitional backend export if needed while TASK-025 remains deferred.
7. STORY-004: complete the climate reading contract; recheck BUG-007 integration when replacing the scalar return with a reading object.
8. STORY-006: complete persistence/history/error boundaries; recheck save/read behavior and dispatch-state persistence without claiming full STORY-008 acceptance.
9. BUG-012: verify analysis and history rendering against repaired backend responses and current schema.

Use one specialist invocation per executable: eight story-builder invocations for backend/container/dependency items and one dashboard-designer invocation for BUG-012, with qa-engineer checks and contract-auditor evidence per handoff. These nine delegations and review overhead are not additional story points. QA must test each touched slice and report actual total/touched-file coverage; the whole-backend 70% floor is not waived because TEST-001 is deferred.

The narrow P0 fixes do not depend on full uncommitted rewrites: the existing publisher returns a message ID, the analyzer and service skeleton entry points exist, and the API/dash repairs can compose those boundaries. Full schema-valid API inputs, safe errors, readiness SLOs, full stored/returned provenance, reproducible root-context non-root packaging, and deployed end-to-end acceptance are not claimed as delivered by planning.

## Deferred ready work

All 19 remaining ready items are deferred because capacity is exhausted, not blocked artificially.

| Item      | Points | Deferral reason                                                                                                                                    |
| --------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| STORY-007 | 3      | Highest remaining P1; does not fit the two points left when encountered.                                                                           |
| STORY-003 | 2      | Paired real-model ranking evidence is useful but below live pipeline fixes.                                                                        |
| STORY-005 | 2      | Complete fallback metadata, safe diagnostics and programming-error distinction remain separate from BUG-010's narrow repair.                       |
| STORY-012 | 2      | Broad safe HTTP error mapping beyond selected CORS repair.                                                                                         |
| STORY-013 | 1      | Full HTTP history acceptance beyond selected persistence helper work.                                                                              |
| TASK-004  | 2      | Runtime IAM work; deployment epic is below this pipeline slice.                                                                                    |
| STORY-022 | 3      | Broad offline-fixture/test migration; scoped QA remains required for selected items.                                                               |
| BUG-006   | 1      | Validator UTC audit correction, not the live coroutine failure.                                                                                    |
| TASK-014  | 1      | Topic override configuration debt.                                                                                                                 |
| TEST-001  | 1      | Explicit whole-backend coverage follow-up; no waiver of NFR-9.                                                                                     |
| TASK-016  | 1      | Artifact-location process prevention.                                                                                                              |
| TASK-017  | 1      | Regression-case process prevention.                                                                                                                |
| TASK-018  | 1      | Complete-criteria handoff prevention.                                                                                                              |
| TASK-019  | 1      | Caller-validation/ownership prevention.                                                                                                            |
| TASK-020  | 1      | Durable planning-guard prevention; current manual checks are not task completion.                                                                  |
| TASK-021  | 1      | Discoverable-test and verification-integrity prevention.                                                                                           |
| TASK-023  | 1      | Durable delegation-budget process improvement.                                                                                                     |
| BUG-013   | 2      | Configurable local API URL, timeout and safe dashboard errors remain known gaps; existing deployed URL is not treated as configuration compliance. |
| TASK-025  | 2      | Full multi-stage/non-root/pinned-tool/PORT/root-context Docker hardening remains known debt.                                                       |

## Genuine remaining blockers

Every item below retains blocked status; where status and priority did not change, only blocker descriptions were reconciled with shipped/current dependencies.

| Item      | Uncommitted prerequisite or human decision                                                           |
| --------- | ---------------------------------------------------------------------------------------------------- |
| STORY-008 | STORY-007; STORY-006 is committed, not a blocker.                                                    |
| STORY-009 | STORY-005, STORY-007; OQ-5 readiness timeout limits.                                                 |
| STORY-010 | STORY-003, STORY-005, STORY-007, STORY-008, STORY-011, STORY-012, STORY-029; OQ-2 temperature range. |
| STORY-011 | OQ-2 exact upload byte limit only; foundation blocker cleared.                                       |
| STORY-014 | STORY-010, STORY-013, TASK-025; BUG-011/TASK-024 committed; frontend dependency removed.             |
| STORY-015 | STORY-014, TASK-004.                                                                                 |
| STORY-016 | STORY-015, STORY-010.                                                                                |
| STORY-017 | STORY-010, STORY-013, STORY-029.                                                                     |
| STORY-018 | STORY-017, STORY-003.                                                                                |
| STORY-019 | STORY-017.                                                                                           |
| STORY-020 | STORY-017, STORY-008.                                                                                |
| STORY-021 | STORY-017; OQ-5 dashboard timeout limits.                                                            |
| STORY-023 | STORY-022, STORY-003, STORY-005, STORY-007, STORY-030.                                               |
| STORY-024 | STORY-022, STORY-010, STORY-011, STORY-012, STORY-013, STORY-029.                                    |
| STORY-025 | STORY-022, STORY-030.                                                                                |
| TASK-005  | STORY-023, STORY-024, STORY-025.                                                                     |
| STORY-026 | STORY-015; shipped foundation no longer a blocker.                                                   |
| STORY-027 | STORY-010, STORY-008, STORY-031.                                                                     |
| STORY-028 | STORY-016, STORY-017, STORY-020, STORY-021, STORY-026; OQ-4.                                         |
| TASK-006  | STORY-016, STORY-028, STORY-026, STORY-027, TASK-005; OQ-4.                                          |
| STORY-029 | STORY-030.                                                                                           |
| STORY-030 | Agreed serialized per-field provenance contract; removed reverse STORY-029 dependency.               |
| STORY-031 | STORY-010; STORY-006 committed.                                                                      |
| STORY-032 | STORY-029, STORY-011; OQ-2.                                                                          |
| TASK-011  | Human-owned edits to protected story/epic documentation.                                             |
| TASK-013  | Human deployment authorization and verified live provisioning/acceptance.                            |
| TASK-015  | Human provisioning, approved ADC/Vertex checks and real GCS upload evidence.                         |
| TASK-022  | Human-approved safe template/editor policy or explicit human handoff.                                |

## Final bl stats

```json
{
  "current_sprint": 2,
  "total": 80,
  "open": 65,
  "open_bugs": 8,
  "by_status": {
    "groomed": 9,
    "ready": 19,
    "in_sprint": 9,
    "done": 15,
    "blocked": 28
  },
  "by_type": {
    "epic": 9,
    "story": 32,
    "task": 25,
    "bug": 13,
    "test": 1
  },
  "loop_done": false
}
```

Single next action: hand BUG-010 to story-builder when Phase 5 is explicitly authorized. Stop here; Phase 5 has not started. This is a planning record, not sprint-02.md completion evidence and not a sign-off verdict.