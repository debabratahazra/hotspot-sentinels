# Phase Procedures

`BL` below is shorthand for:

```bash
python3 .github/skills/agile-sdlc-loop/scripts/backlog.py
```

Item types: `epic`, `story`, `task`, `bug`, `test`. Statuses flow
`new -> groomed -> ready -> in_sprint -> in_progress -> in_review -> done`, with `blocked` and `cancelled` as exits.

---

## Phase 0 — Requirements

**Agent:** `product-owner`

1. `BL init` if `agile/backlog.json` does not exist.
2. Write `agile/requirements.md`. Source it from [COPILOT_GUIDE.md](../../../../COPILOT_GUIDE.md) and [Epics_Stories.md](../../../../Epics_Stories.md), plus whatever the user adds. Structure:
   - **Product goal** — one paragraph.
   - **Functional requirements** — numbered `FR-1`, `FR-2`, … Each is one testable capability.
   - **Non-functional requirements** — numbered `NFR-1`, … covering performance, security, cost, region, units.
   - **Out of scope** — explicit exclusions.
   - **Open questions** — anything you could not resolve.
3. If Open questions is non-empty, ask the user before proceeding.

**Exit:** `agile/requirements.md` exists, every requirement has a stable ID, no blocking open questions.

---

## Phase 1 — Epics

**Agent:** `product-owner`

1. Group requirements into epics — one epic per coherent capability, 3–8 total.
2. `BL add --type epic --title "..." --description "Delivers FR-1, FR-3" --priority P1`
3. Every functional requirement must appear in exactly one epic. State the coverage map.

**Exit:** every `FR-*` maps to an epic; no epic exists without a requirement.

---

## Phase 2 — User stories

**Agent:** `product-owner`

For each epic, write vertical slices a developer can finish in one sitting.

```bash
BL add --type story --parent EPIC-001 \
  --title "As an analyst I can score a zone from an uploaded aerial image" \
  --description "..." --priority P1 --estimate 3 \
  --ac "POST /api/analyze returns a schema-valid report" "HVI 1.0-10.0" "risk_level matches the band" \
  --files backend/main.py backend/services/vision_analyzer.py
```

Rules:
- Title uses "As a &lt;role&gt; I can &lt;outcome&gt;". No "implement X" titles.
- 2–5 acceptance criteria, each independently checkable. These become the test cases in phase 6.
- Estimate 1, 2, 3, 5, or 8. Anything above 8 must be split.
- `--files` lists the expected touch points so `story-builder` can pick it up without re-deriving scope.

**Exit:** every epic has at least one story; no story estimates above 8; all have acceptance criteria.

---

## Phase 3 — Grooming and prioritisation

**Agent:** `scrum-master`

1. `BL list --status new` and review each item.
2. Reject or fix: missing acceptance criteria, estimate above 8, duplicate of an existing item, no parent epic, or no traceable requirement. Split with `BL add`, retire with `--status cancelled`.
3. Set priority:

   | Priority | Meaning                                                                   |
   | -------- | ------------------------------------------------------------------------- |
   | `P0`     | Broken build, failing tests, security defect, data loss — jumps the queue |
   | `P1`     | Required for the product to function end to end                           |
   | `P2`     | Valuable but the product works without it                                 |
   | `P3`     | Nice to have, polish, tech debt with no current pain                      |

   Dependency rule: a story cannot outrank a story it depends on. In this codebase `vision_analyzer`, `climate_service`, `alert_dispatcher`, and `database` all precede `main.py`, which precedes the Streamlit app.
4. `BL update <id> --status ready --priority P1 --estimate 3` once an item is complete and correctly ranked.

**Exit:** no `new` items remain; everything is `ready`, `blocked`, or `cancelled`.

---

## Phase 4 — Sprint planning

**Agent:** `scrum-master`

1. Set capacity. Default 8 points; use the previous sprint's completed points once history exists.
2. Write a one-sentence sprint goal naming the user-visible outcome.
3. `BL plan --capacity 8 --goal "Analyse an image end to end and persist the report"`
4. Print the committed list and confirm no committed story depends on an uncommitted one.
5. For every committed item that deliberately changes observable behaviour, name the tests that encode the current contract **before** work starts, and fold the cost of updating them into that item's estimate. Find them rather than guessing:
   ```bash
   grep -rln "<changed field, route, label or form name>" tests/
   ```
   Record the list in the item's description. An item whose behaviour change is unbudgeted is not ready to commit. Stale-test churn was mistaken for regression in four consecutive sprints (3–6), and deleting two scripts in sprint 7 invalidated three further assertions.
6. **Scope added mid-sprint gets the same treatment.** Authorised unplanned work is still work: before it starts, name the tests it invalidates and add that cost to its estimate, then rebaseline the sprint total out loud. Sprint 7 ran 27 points against a 15-point commitment; that was acceptable because it was declared, not absorbed.

**Exit:** a sprint exists with committed items; every committed item is `in_sprint`, and every behaviour-changing item names the tests it will invalidate.

---

## Phase 5 — Develop

**Agent:** `story-builder`, or `dashboard-designer` for `frontend/` work

For each committed item in priority order:

1. `BL update <id> --status in_progress`
2. **Check the agent can do the job before dispatching it.** Confirm the chosen agent is write-capable when the item produces files, and that every path the item needs is in its permitted set. `product-owner` and `contract-auditor` cannot edit application files; routing file-writing work to them wastes a round trip and forces the orchestrator to redo it.
3. Delegate with the story title, acceptance criteria, and `files`. Record the dispatch: item ID, exact instructions, permitted files, and evidence already gathered — never credentials or tokens.
4. On success `BL update <id> --status in_review`. If blocked, `--status blocked` with the reason in the description, and move on.

**When a run fails, separate the cause before retrying:**

| Failure                                           | Action                                                                                         |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Transient (auth expiry, timeout)                  | Redispatch the same item from the recorded dispatch state; do not repeat completed exploration |
| Task failure (agent did the work and it is wrong) | Treat as a finding, not a retry                                                                |
| Permanent authorization failure                   | `--status blocked` for a human; never retry in a loop                                          |

**Reviewing an item that accepts caller input:** require schema validation at the
report boundary for every externally supplied override, including out-of-range
values, missing fields, and aliasing. Evidence must include a rejected
out-of-range coordinate and a proof that the returned report does not alias the
caller's dict — BUG-001 returned caller coordinates by reference and let
`lat=999.0` through.

**Exit:** every committed item is `in_review`, `blocked`, or `cancelled`.

---

## Phase 6 — Test and coverage

**Agent:** `qa-engineer`

1. For each `in_review` item, write tests under `tests/` — one test per acceptance criterion, named for the criterion.
2. Run the suite and generate the coverage data:
   ```bash
   python3 .github/skills/agile-sdlc-loop/scripts/sprint_report.py
   ```
3. Record the run verdict as exactly one of three outcomes. There is no fourth, and absence of a failure is not a pass:

   | Verdict        | When                                              | Required evidence                                |
   | -------------- | ------------------------------------------------- | ------------------------------------------------ |
   | `PASS`         | The run completed and every test passed           | exact command, pass count, duration              |
   | `FAIL`         | The run completed with at least one failure       | exact command, each failing test id              |
   | `INCONCLUSIVE` | Timed out, interrupted, or no result was produced | exact command, the reason, a deterministic rerun |

   An `INCONCLUSIVE` run is never reported as `PASS` and never closes an item. Rerun it to completion and report the completed run instead. A long suite finishes reliably under an explicit timeout:
   ```bash
   python3 -m pytest -o addopts='' -q   # record this exact line with the verdict
   ```
4. Triage results:
   - Test passes → `BL update <id> --status done`
   - Test fails → `BL add --type bug --parent <story-id> --priority P0 --source qa --title "..." --description "<repro + expected vs actual>"`, story stays `in_review`, return to phase 5.
   - Coverage below 70% on a touched file → `BL add --type test --source qa --priority P2 --title "Raise coverage for <file>"`.
5. Repeat until the suite is green or the remaining failures are logged as bugs with owners.

**Exit:** an authoritative completed run exists with its command and verdict recorded; the suite is green, or every failure is captured as a `P0` bug. Coverage recorded. An `INCONCLUSIVE` run does not satisfy this exit.

---

## Phase 7 — Deploy

**Agent:** `cloud-deployer`

Skip if the build is red — a failing suite never deploys.

1. Build from the repository root: `docker build -f backend/Dockerfile -t "$IMAGE" .`
2. Deploy to Cloud Run in `asia-southeast1` on port 8080. The hook will ask for confirmation; wait for it.
3. If the user does not confirm, `BL add --type task --source validation --title "Deploy sprint N build"` with `--status blocked` and continue to phase 8 against the local server instead.

**Exit:** a revision is serving and `/api/health` returns 200, or the deploy task is explicitly `blocked`.

---

## Phase 8 — Validate

**Agent:** `contract-auditor`, plus the `heat-report-validation` skill

1. Walk the acceptance criteria of each `done` story against the running system. A criterion that cannot be demonstrated sends the story back to `in_review`.
2. Run the contract audit for schema drift, units, SDK, region, secrets, and layering.
3. Validate a live analysis payload:
   ```bash
   python3 .github/skills/heat-report-validation/scripts/validate_report.py /tmp/analyze.json
   ```
4. File every `BLOCKER` and `MAJOR` finding as a bug with `--source validation`.

**Exit:** each `done` story is demonstrated; all findings are backlog items.

---

## Phase 9 — Sprint report

**Agent:** `scrum-master`

```bash
python3 .github/skills/agile-sdlc-loop/scripts/sprint_report.py <sprint-number>
```

Writes `agile/reports/sprint-NN.md` with committed vs completed, carry-over, test result, per-file coverage, files below the 70% floor, and open bugs. Summarise it in chat with the velocity (points completed) — that number sets the next sprint's capacity.

**Exit:** the report file exists and has been summarised.

---

## Phase 10 — Retrospective

**Agent:** `scrum-master`

1. Derive findings from evidence in the sprint, not from sentiment. Look at carry-over, bug counts, coverage deltas, blocked items, and audit findings.
2. Record them:
   ```bash
   BL close-sprint \
     --went-well "Vision analyzer landed with 92% coverage" \
     --improve "Acceptance criteria were too vague to test directly" \
     --went-wrong "Deploy blocked on missing IAM role"
   ```
   Closing the sprint returns unfinished committed items to `ready` automatically.
3. Convert every `improve` and `went_wrong` finding into a backlog item with `--source retro`. A finding with no item is not a finding.
   - Went wrong → `bug` or `task` at `P0`/`P1`
   - Needs improvement → `task` at `P1`/`P2`
   - Went well → no item; note it in the report so the practice is kept

**Exit:** sprint closed, retro recorded, findings converted.

---

## Phase 11 — Sprint sign-off

**Agent:** none — you run this yourself and then stop.

1. Run the mechanical gate:
   ```bash
   BL gate
   ```
   It exits non-zero and names the failures if any committed item is not `done`, anything is `blocked`, an open `P0` exists, or the sprint report is missing.
2. Add the judgement the gate cannot make: were the acceptance criteria actually demonstrated in phase 8, and does the delivered behaviour match the sprint goal? A green gate with undemonstrated criteria is still a rejection.
3. Print the verdict:

   | Verdict                    | Meaning                                                      |
   | -------------------------- | ------------------------------------------------------------ |
   | `ACCEPTED`                 | Gate passed and every criterion was demonstrated             |
   | `ACCEPTED WITH CARRY-OVER` | Goal met; unfinished items returned to `ready` and are named |
   | `REJECTED`                 | Gate failed — list each failing check and the item IDs       |

4. Report: goal vs delivered, velocity in points, test verdict, total coverage and delta, report path, retro findings with their new backlog IDs, `stats`, and the proposed next sprint contents.
5. Ask **"Accept sprint N and plan sprint N+1?"** and **end your turn**.

Do not plan, groom, or write code past this point. The next sprint starts only on a fresh instruction.

**Exit:** verdict printed, question asked, turn ended.
