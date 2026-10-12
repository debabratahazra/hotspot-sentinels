"""Add the location discovery epic and stories (sprint 9 extension)."""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "agile/backlog.json"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

EPIC = {
    "id": "EPIC-016",
    "title": "Location Discovery",
    "description": (
        "Let an operator reach any location in the world, not just the five presets. Three input "
        "methods that all resolve to the same latitude/longitude pair the analysis already takes: the "
        "existing preset shortcuts, a search by city or area name, and a click on a world map. "
        "Geocoding runs on the backend so GOOGLE_MAPS_API_KEY is never exposed to the browser."
    ),
    "priority": "P1",
}

STORIES = [
    {
        "id": "STORY-049",
        "title": "As an operator I can search any city or area by name",
        "estimate": 5,
        "priority": "P1",
        "acceptance_criteria": [
            "Searching a place name sets the latitude and longitude used by the analysis.",
            "The resolved place is shown back to the operator so a wrong match is obvious before analysing.",
            "A search with no match produces a clear message and leaves the previous coordinates unchanged.",
            "Geocoding happens server-side; GOOGLE_MAPS_API_KEY never reaches the browser, the logs, or a client error.",
            "A geocoding outage degrades to a clear message and never breaks the analysis path.",
        ],
        "files": ["backend/tools/geocoding_service.py", "backend/main.py", "frontend/app.py"],
    },
    {
        "id": "STORY-050",
        "title": "As an operator I can click anywhere on a world map to choose a location",
        "estimate": 5,
        "priority": "P2",
        "acceptance_criteria": [
            "Clicking a point on the map sets the latitude and longitude used by the analysis.",
            "The chosen point is visibly marked and its coordinates are displayed.",
            "The map, the search box and the preset shortcuts all drive the same coordinate pair without conflicting.",
            "A click outside valid coordinate ranges is rejected rather than sent to the backend.",
        ],
        "files": ["frontend/app.py"],
    },
]


def main() -> None:
    data = json.loads(BACKLOG.read_text())
    existing = {item["id"] for item in data["items"]}

    if EPIC["id"] not in existing:
        data["items"].append({
            "id": EPIC["id"], "type": "epic", "parent": None,
            "title": EPIC["title"], "description": EPIC["description"],
            "acceptance_criteria": [], "priority": EPIC["priority"],
            "estimate": None, "status": "groomed", "sprint": 9,
            "files": [], "source": "hackathon-enhancement",
            "created": NOW, "updated": NOW,
        })
        print(f"  + {EPIC['id']}  {EPIC['title']}")

    for story in STORIES:
        if story["id"] in existing:
            print(f"  {story['id']} already present, skipping")
            continue
        data["items"].append({
            "id": story["id"], "type": "story", "parent": EPIC["id"],
            "title": story["title"], "description": "",
            "acceptance_criteria": story["acceptance_criteria"],
            "priority": story["priority"], "estimate": story["estimate"],
            "status": "groomed", "sprint": 9, "files": story["files"],
            "source": "hackathon-enhancement", "created": NOW, "updated": NOW,
        })
        print(f"  + {story['id']}  [{story['estimate']}pt] {story['title'][:60]}")

    BACKLOG.write_text(json.dumps(data, indent=2) + "\n")
    print(f"\n  added {sum(s['estimate'] for s in STORIES)} points to sprint 9")


if __name__ == "__main__":
    main()
