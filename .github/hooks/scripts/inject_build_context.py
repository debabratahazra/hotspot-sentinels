#!/usr/bin/env python3
"""SessionStart: tell the agent which backlog stories are already built."""

import json
import sys
from pathlib import Path

STORIES = (
    ("1.1", "backend/services/vision_analyzer.py"),
    ("1.2", "backend/tools/seed_samples.py"),
    ("2.1", "backend/tools/climate_service.py"),
    ("3.1", "backend/services/alert_dispatcher.py"),
    ("3.2", "backend/services/database.py"),
    ("4.1", "backend/main.py"),
    ("4.2", "backend/Dockerfile"),
    ("5.1", "frontend/app.py"),
)


def main():
    done = [(story, path) for story, path in STORIES if Path(path).is_file()]
    todo = [(story, path) for story, path in STORIES if not Path(path).is_file()]

    lines = [f"HotSpot Sentinels build state: {len(done)}/{len(STORIES)} stories done."]
    if todo:
        story, path = todo[0]
        lines.append(f"Next story: {story} -> {path}")
    else:
        lines.append("All backlog stories exist.")
    lines.append("Configured: .env present." if Path(".env").is_file() else "Configured: .env MISSING — ./setup_gcp.sh has not been run.")

    context = "\n".join(lines)
    json.dump(
        {
            "systemMessage": context,
            "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context},
        },
        sys.stdout,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
