"""Add the Firebase experience epics and their stories to the backlog.

One-shot helper for sprint 9 planning; safe to re-run (it skips ids already present).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "agile/backlog.json"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

EPICS = [
    {
        "id": "EPIC-012",
        "title": "Public Real-Time Heat Alert Wall",
        "description": (
            "A citizen-facing page on Firebase Hosting that subscribes to Firestore in real time and "
            "shows CRITICAL zones the moment they are detected. Deliberately a separate artifact from "
            "the Streamlit operator dashboard so the working demo path is never put at risk. Publishes "
            "to a curated public_alerts collection rather than exposing hotspot_scans, so only chosen "
            "fields are world-readable."
        ),
        "priority": "P1",
    },
    {
        "id": "EPIC-013",
        "title": "Dashboard Experience Upgrade",
        "description": (
            "Make the operator dashboard more informative and more striking on camera without changing "
            "the API contract: clearer HVI presentation, better surface and blueprint layout, and "
            "visible state transitions. Presentation layer only."
        ),
        "priority": "P2",
    },
    {
        "id": "EPIC-014",
        "title": "City-Wide Heat Map",
        "description": (
            "Plot every persisted scan on one interactive map coloured by risk band, so a viewer sees "
            "the city-scale picture instead of one zone at a time."
        ),
        "priority": "P2",
    },
    {
        "id": "EPIC-015",
        "title": "Operator Identity with Firebase Authentication",
        "description": (
            "Sign-in for the operator dashboard using Firebase Authentication, attributing each scan to "
            "the operator who ran it. Lowest priority of the sprint: it adds a login step to the demo "
            "for limited evaluation value, and will be dropped before anything above it slips."
        ),
        "priority": "P3",
    },
]

STORIES = [
    # EPIC-012 — the alert wall
    {
        "id": "STORY-044",
        "parent": "EPIC-012",
        "title": "As a citizen I see critical heat zones appear live without refreshing",
        "estimate": 5,
        "priority": "P1",
        "acceptance_criteria": [
            "A page served by Firebase Hosting lists current CRITICAL zones newest first.",
            "A new CRITICAL analysis appears on an already-open page within seconds and without a reload.",
            "The page shows zone name, HVI score, risk band, measured ambient temperature and detection time.",
            "With no alerts present the page shows an explicit empty state, never a blank screen or an error.",
        ],
        "files": ["public/index.html", "public/app.js", "firebase.json"],
    },
    {
        "id": "STORY-045",
        "parent": "EPIC-012",
        "title": "As a maintainer I publish only curated fields to the public collection",
        "estimate": 3,
        "priority": "P1",
        "acceptance_criteria": [
            "A CRITICAL analysis writes a record to public_alerts containing only the fields the wall needs.",
            "hotspot_scans itself is never world-readable.",
            "Firestore security rules allow public read of public_alerts and deny all client writes.",
            "A publish failure is logged and never fails the analysis response.",
        ],
        "files": ["backend/services/database.py", "backend/main.py", "firestore.rules"],
    },
    # EPIC-013 — dashboard polish
    {
        "id": "STORY-046",
        "parent": "EPIC-013",
        "title": "As an operator I read the result faster from a clearer layout",
        "estimate": 3,
        "priority": "P2",
        "acceptance_criteria": [
            "The HVI score, risk band and alert state are legible at a glance at presentation scale.",
            "The surface breakdown and cooling blueprint are visually distinct from each other.",
            "No change to the Heat Analysis Result contract or to any API route.",
            "Existing frontend tests still pass without weakening an assertion.",
        ],
        "files": ["frontend/app.py"],
    },
    # EPIC-014 — map
    {
        "id": "STORY-047",
        "parent": "EPIC-014",
        "title": "As a planner I see every analysed zone on one map coloured by risk",
        "estimate": 5,
        "priority": "P2",
        "acceptance_criteria": [
            "Persisted scans with coordinates render as markers coloured by risk band.",
            "Selecting a marker shows that zone's HVI, risk band and measured temperature.",
            "A scan without coordinates is skipped without breaking the map.",
            "The map degrades to an explicit message when no scans are available.",
        ],
        "files": ["frontend/app.py"],
    },
    # EPIC-015 — auth, explicitly last
    {
        "id": "STORY-048",
        "parent": "EPIC-015",
        "title": "As an operator I sign in before running an analysis",
        "estimate": 5,
        "priority": "P3",
        "acceptance_criteria": [
            "An unauthenticated visitor cannot trigger an analysis.",
            "A signed-in operator's identifier is recorded on the scans they create.",
            "Sign-in failure produces a clear message and never exposes a token or credential.",
            "The deployed demo path still works end to end with authentication enabled.",
        ],
        "files": ["frontend/app.py", "backend/main.py"],
    },
]


def main() -> None:
    data = json.loads(BACKLOG.read_text())
    existing = {item["id"] for item in data["items"]}
    added = 0

    for epic in EPICS:
        if epic["id"] in existing:
            print(f"  {epic['id']} already present, skipping")
            continue
        data["items"].append({
            "id": epic["id"], "type": "epic", "parent": None,
            "title": epic["title"], "description": epic["description"],
            "acceptance_criteria": [], "priority": epic["priority"],
            "estimate": None, "status": "groomed", "sprint": 9,
            "files": [], "source": "hackathon-enhancement",
            "created": NOW, "updated": NOW,
        })
        added += 1
        print(f"  + {epic['id']}  {epic['title']}")

    for story in STORIES:
        if story["id"] in existing:
            print(f"  {story['id']} already present, skipping")
            continue
        data["items"].append({
            "id": story["id"], "type": "story", "parent": story["parent"],
            "title": story["title"], "description": "",
            "acceptance_criteria": story["acceptance_criteria"],
            "priority": story["priority"], "estimate": story["estimate"],
            "status": "groomed", "sprint": 9, "files": story["files"],
            "source": "hackathon-enhancement", "created": NOW, "updated": NOW,
        })
        added += 1
        print(f"  + {story['id']}  [{story['estimate']}pt] {story['title'][:58]}")

    data["current_sprint"] = 9
    BACKLOG.write_text(json.dumps(data, indent=2) + "\n")
    print(f"\n  {added} items added; current_sprint = 9")
    print(f"  committed points: {sum(s['estimate'] for s in STORIES)}")


if __name__ == "__main__":
    main()
