# EPIC-04 — Event-Driven Resilience Pipeline

|                |                                                                                                                      |
| -------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Goal**       | Persist every scan for later review, and page someone automatically when a zone crosses the critical heat threshold. |
| **Source**     | [Epics_Stories.md](../../../Epics_Stories.md) Epic 3                                                                 |
| **Priority**   | P1                                                                                                                   |
| **Status**     | Not started                                                                                                          |
| **Depends on** | EPIC-01                                                                                                              |
| **Delivers**   | `backend/services/database.py`, `backend/services/alert_dispatcher.py`                                               |

## Why this epic exists

A one-shot analysis is a toy. Storing scans turns the product into a record of how a city's heat profile changes; publishing alerts turns it from a report into a response. These are the two halves of "resilience" in the project name.

## Scope

**In:** the Firestore `hotspot_scans` collection, the Pub/Sub critical alert, and the failure policy for each.

**Out:** subscribers, notification channels, dashboards over history. Publishing the event is where this epic ends.

## Failure policy

The two services fail differently on purpose:

| Service   | On failure                               | Why                                                                 |
| --------- | ---------------------------------------- | ------------------------------------------------------------------- |
| Firestore | Raise `DatabaseError` → API returns 503  | A scan the user believes was saved but was not is a correctness bug |
| Pub/Sub   | Log, return `""`, request still succeeds | A failed alert must not destroy an otherwise good analysis          |

## Stories

### Story 4.1 — Firestore scan store
- **File:** `backend/services/database.py`
- **Estimate:** 3 · **Priority:** P1 · **Status:** Not started
- **Source:** original Story 3.2
- **Required API:**
  ```python
  def save_hotspot_report(report: dict) -> str
  def get_recent_reports(limit: int = 10) -> list[dict]
  ```
- **Acceptance criteria:**
  - [ ] Collection name is the module constant `COLLECTION_NAME = "hotspot_scans"`
  - [ ] `save_hotspot_report` writes the full report and returns the generated document ID
  - [ ] Sets `created_at` with `firestore.SERVER_TIMESTAMP` when `timestamp` is absent
  - [ ] `get_recent_reports` orders by `timestamp` descending and applies `limit`
  - [ ] `limit` clamped to 1–100 — an unbounded read is a denial-of-service vector
  - [ ] Firestore timestamps converted to ISO-8601 strings so FastAPI can serialise them
  - [ ] Raises `DatabaseError` on failure; the raw SDK exception never crosses the boundary
  - [ ] Client cached at module level; functions stay synchronous

### Story 4.2 — Pub/Sub critical alert dispatcher
- **File:** `backend/services/alert_dispatcher.py`
- **Estimate:** 3 · **Priority:** P1 · **Status:** Not started
- **Source:** original Story 3.1
- **Required API:**
  ```python
  def dispatch_heat_alert(zone_data: dict) -> str
  ```
- **Acceptance criteria:**
  - [ ] `CRITICAL_HVI_THRESHOLD = 8.0` as a module constant
  - [ ] Publishes only when `hvi_score >= 8.0`; below threshold returns `""` without constructing a client
  - [ ] Topic from `PUBSUB_TOPIC_ID`, path built with `publisher.topic_path(...)`
  - [ ] Payload is UTF-8 JSON with `zone_id`, `zone_name`, `coordinates`, `ambient_temp_c`, `hvi_score`, `risk_level`, the urgent interventions, and `dispatched_at`
  - [ ] Attributes `risk_level` and `zone_id` set so subscribers can filter without decoding the body
  - [ ] Returns the resolved message ID from `future.result(timeout=...)`
  - [ ] Publish failure logs and returns `""` — it never raises
  - [ ] No credentials or image bytes in the payload

### Story 4.3 — Alert provenance
- **Files:** `backend/services/alert_dispatcher.py`, `backend/main.py`
- **Estimate:** 1 · **Priority:** P2 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] `alert_dispatched` is set from whether a message ID came back, never guessed by the model
  - [ ] A stored report's `alert_dispatched` matches what actually happened
  - [ ] `alert_dispatched` is never `true` when `hvi_score < 8.0` — `validate_report.py` enforces this

## Definition of done

A critical report produces a real message ID and a Firestore document whose `alert_dispatched` is `true`; a sub-threshold report produces neither. Both services are covered by mocked tests in EPIC-08 that need no credentials.

## Risks

| Risk                                             | Mitigation                                                                                   |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Alert failure breaking a good analysis           | Best-effort publish, empty string on failure                                                 |
| Unbounded Firestore reads                        | Clamp `limit` to 100                                                                         |
| Firestore timestamps breaking JSON serialisation | Convert to ISO-8601 at this boundary                                                         |
| Threshold drifting from the UI badge             | 8.0 defined once per layer and audited each sprint                                           |
| Alert storm during a demo                        | Threshold is deliberately high; the dashboard shows dispatch state rather than re-triggering |

## Seed the backlog

```bash
bl() { python3 .github/skills/agile-sdlc-loop/scripts/backlog.py "$@"; }
bl add --type epic --title "Event-Driven Resilience Pipeline" --priority P1 \
  --description "Firestore persistence for scans and Pub/Sub alerts above the critical HVI threshold"
bl add --type story --parent EPIC-004 --priority P1 --estimate 3 --source requirements \
  --title "As an analyst I can see my previous scans" \
  --files backend/services/database.py \
  --ac "save returns a document id" \
       "recent reports ordered by timestamp descending" \
       "limit clamped to 1-100" \
       "timestamps JSON-serializable" \
       "DatabaseError raised on failure"
bl add --type story --parent EPIC-004 --priority P1 --estimate 3 --source requirements \
  --title "As an ops lead I am alerted automatically when a zone becomes critical" \
  --files backend/services/alert_dispatcher.py \
  --ac "publishes only at hvi_score >= 8.0" \
       "returns empty string below threshold with no client call" \
       "message carries coordinates, temperature and urgent actions" \
       "publish failure returns empty string and does not raise"
bl add --type story --parent EPIC-004 --priority P2 --estimate 1 --source requirements \
  --title "As an auditor I can trust the alert_dispatched flag on a stored scan" \
  --files backend/services/alert_dispatcher.py backend/main.py \
  --ac "alert_dispatched set from the returned message id" \
       "never true below hvi 8.0"
```
