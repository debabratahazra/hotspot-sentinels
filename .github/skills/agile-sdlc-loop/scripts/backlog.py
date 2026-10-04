#!/usr/bin/env python3
"""Backlog state for the agile SDLC loop. Stdlib only, JSON-backed."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BACKLOG = ROOT / "agile" / "backlog.json"

TYPES = ("epic", "story", "task", "bug", "test")
PRIORITIES = ("P0", "P1", "P2", "P3")
STATUSES = ("new", "groomed", "ready", "in_sprint", "in_progress", "in_review", "done", "blocked", "cancelled")
OPEN_STATUSES = ("new", "groomed", "ready", "in_sprint", "in_progress", "in_review", "blocked")
PREFIX = {"epic": "EPIC", "story": "STORY", "task": "TASK", "bug": "BUG", "test": "TEST"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load() -> dict:
    if not BACKLOG.is_file():
        sys.exit(f"No backlog at {BACKLOG}. Run: backlog.py init")
    return json.loads(BACKLOG.read_text(encoding="utf-8"))


def save(data: dict) -> None:
    BACKLOG.parent.mkdir(parents=True, exist_ok=True)
    BACKLOG.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def next_id(data: dict, item_type: str) -> str:
    prefix = PREFIX[item_type]
    used = [int(i["id"].split("-")[1]) for i in data["items"] if i["id"].startswith(prefix + "-")]
    return f"{prefix}-{max(used, default=0) + 1:03d}"


def find(data: dict, item_id: str) -> dict:
    for item in data["items"]:
        if item["id"].upper() == item_id.upper():
            return item
    sys.exit(f"Unknown id: {item_id}")


def is_open(item: dict, items: list) -> bool:
    """An epic stops counting as open once every child is resolved; a childless epic still needs stories."""
    if item["status"] not in OPEN_STATUSES:
        return False
    if item["type"] == "epic":
        children = [c for c in items if c.get("parent") == item["id"]]
        if children and all(c["status"] in ("done", "cancelled") for c in children):
            return False
    return True


def close_finished_epics(data: dict) -> list:
    closed = []
    for epic in [i for i in data["items"] if i["type"] == "epic" and i["status"] not in ("done", "cancelled")]:
        children = [c for c in data["items"] if c.get("parent") == epic["id"]]
        if children and all(c["status"] in ("done", "cancelled") for c in children):
            epic.update(status="done", updated=now())
            closed.append(epic["id"])
    return closed


def cmd_init(args) -> None:
    if BACKLOG.is_file() and not args.force:
        sys.exit(f"Backlog already exists at {BACKLOG}. Pass --force to reset.")
    save({"version": 1, "product": args.product, "current_sprint": 0, "sprints": [], "items": []})
    print(f"Initialised {BACKLOG}")


def cmd_add(args) -> None:
    data = load()
    item = {
        "id": next_id(data, args.type),
        "type": args.type,
        "parent": args.parent,
        "title": args.title,
        "description": args.description or "",
        "acceptance_criteria": args.ac or [],
        "priority": args.priority,
        "estimate": args.estimate,
        "status": args.status,
        "sprint": None,
        "files": args.files or [],
        "source": args.source,
        "created": now(),
        "updated": now(),
    }
    data["items"].append(item)
    save(data)
    print(item["id"])


def cmd_update(args) -> None:
    data = load()
    item = find(data, args.id)
    for field in ("status", "priority", "estimate", "title", "description", "parent", "source"):
        value = getattr(args, field)
        if value is not None:
            item[field] = value
    if args.sprint is not None:
        item["sprint"] = args.sprint
    if args.ac:
        item["acceptance_criteria"] = args.ac
    if args.files:
        item["files"] = args.files
    item["updated"] = now()
    save(data)
    print(f"{item['id']} -> {item['status']} (P:{item['priority']} sprint:{item['sprint']})")


def sort_key(item: dict):
    return (PRIORITIES.index(item["priority"]), item["created"])


def cmd_list(args) -> None:
    data = load()
    items = data["items"]
    if args.status:
        items = [i for i in items if i["status"] in args.status]
    if args.type:
        items = [i for i in items if i["type"] in args.type]
    if args.sprint is not None:
        items = [i for i in items if i["sprint"] == args.sprint]
    if args.parent:
        items = [i for i in items if i["parent"] == args.parent]
    items = sorted(items, key=sort_key)

    if args.json:
        json.dump(items, sys.stdout, indent=2)
        return
    if not items:
        print("(no matching items)")
        return
    for item in items:
        sprint = f"S{item['sprint']}" if item["sprint"] else "--"
        print(f"{item['id']:<10} {item['priority']} {sprint:<4} {item['status']:<12} {item['type']:<6} {item['title']}")


def cmd_plan(args) -> None:
    """Pull the highest-priority ready items into the next sprint, up to capacity."""
    data = load()
    ready = sorted((i for i in data["items"] if i["status"] == "ready"), key=sort_key)
    if not ready:
        sys.exit("Nothing is 'ready'. Groom items first: backlog.py update <id> --status ready")

    sprint_no = data["current_sprint"] + 1
    selected, load_points = [], 0
    for item in ready:
        if load_points + item["estimate"] > args.capacity and selected:
            continue
        item.update(status="in_sprint", sprint=sprint_no, updated=now())
        selected.append(item)
        load_points += item["estimate"]

    data["current_sprint"] = sprint_no
    data["sprints"].append({"number": sprint_no, "goal": args.goal, "capacity": args.capacity,
                            "committed": [i["id"] for i in selected], "started": now(), "closed": None, "retro": None})
    save(data)
    print(f"Sprint {sprint_no} planned — {len(selected)} item(s), {load_points}/{args.capacity} points")
    for item in selected:
        print(f"  {item['id']:<10} {item['priority']} ({item['estimate']}) {item['title']}")


def cmd_close_sprint(args) -> None:
    data = load()
    sprint = next((s for s in data["sprints"] if s["number"] == data["current_sprint"]), None)
    if not sprint:
        sys.exit("No open sprint.")

    committed = [i for i in data["items"] if i["sprint"] == sprint["number"]]
    done = [i for i in committed if i["status"] == "done"]
    for item in committed:
        if item["status"] not in ("done", "cancelled"):
            item.update(status="ready", sprint=None, updated=now())

    sprint["closed"] = now()
    sprint["completed"] = [i["id"] for i in done]
    sprint["carried_over"] = [i["id"] for i in committed if i not in done]
    sprint["retro"] = {"went_well": args.went_well or [], "improve": args.improve or [], "went_wrong": args.went_wrong or []}
    closed_epics = close_finished_epics(data)
    save(data)
    print(f"Sprint {sprint['number']} closed — {len(done)}/{len(committed)} done, "
          f"{len(sprint['carried_over'])} carried over")
    if closed_epics:
        print(f"Epics completed: {', '.join(closed_epics)}")


def cmd_stats(args) -> None:
    data = load()
    items = data["items"]
    by_status = {s: sum(1 for i in items if i["status"] == s) for s in STATUSES}
    by_type = {t: sum(1 for i in items if i["type"] == t) for t in TYPES}
    open_items = [i for i in items if is_open(i, items)]
    stats = {
        "current_sprint": data["current_sprint"],
        "total": len(items),
        "open": len(open_items),
        "open_bugs": sum(1 for i in open_items if i["type"] == "bug"),
        "by_status": {k: v for k, v in by_status.items() if v},
        "by_type": {k: v for k, v in by_type.items() if v},
        "loop_done": not open_items,
    }
    json.dump(stats, sys.stdout, indent=2)
    print()


def cmd_gate(args) -> None:
    """Mechanical sprint sign-off. Exits non-zero when the sprint cannot be accepted."""
    data = load()
    sprint_no = args.sprint or data["current_sprint"]
    sprint = next((s for s in data["sprints"] if s["number"] == sprint_no), None)
    if not sprint:
        sys.exit(f"Sprint {sprint_no} not found.")

    committed = [i for i in data["items"] if i["id"] in sprint.get("committed", [])]
    incomplete = [i for i in committed if i["status"] != "done"]
    blocked = [i for i in committed if i["status"] == "blocked"]
    open_p0 = [i for i in data["items"] if i["priority"] == "P0" and is_open(i, data["items"])]
    report = ROOT / "agile" / "reports" / f"sprint-{sprint_no:02d}.md"

    checks = [
        ("committed_items_done", not incomplete, [i["id"] for i in incomplete]),
        ("nothing_blocked", not blocked, [i["id"] for i in blocked]),
        ("no_open_p0", not open_p0, [i["id"] for i in open_p0]),
        ("sprint_report_written", report.is_file(), report.name),
    ]
    result = {
        "sprint": sprint_no,
        "goal": sprint.get("goal"),
        "committed": len(committed),
        "done": len(committed) - len(incomplete),
        "passed": all(ok for _, ok, _ in checks),
        "checks": [{"check": name, "ok": ok, "detail": detail} for name, ok, detail in checks],
    }
    json.dump(result, sys.stdout, indent=2)
    print()
    sys.exit(0 if result["passed"] else 1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agile backlog state")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create an empty backlog")
    p.add_argument("--product", default="HotSpot Sentinels")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("add", help="add an item")
    p.add_argument("--type", required=True, choices=TYPES)
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--parent")
    p.add_argument("--ac", nargs="*", help="acceptance criteria")
    p.add_argument("--priority", default="P2", choices=PRIORITIES)
    p.add_argument("--estimate", type=int, default=1)
    p.add_argument("--status", default="new", choices=STATUSES)
    p.add_argument("--files", nargs="*")
    p.add_argument("--source", default="manual",
                   choices=("requirements", "grooming", "retro", "qa", "validation", "manual"))
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("update", help="change an item")
    p.add_argument("id")
    p.add_argument("--status", choices=STATUSES)
    p.add_argument("--priority", choices=PRIORITIES)
    p.add_argument("--estimate", type=int)
    p.add_argument("--sprint", type=int)
    p.add_argument("--title")
    p.add_argument("--description")
    p.add_argument("--parent")
    p.add_argument("--source")
    p.add_argument("--ac", nargs="*")
    p.add_argument("--files", nargs="*")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("list", help="query items")
    p.add_argument("--status", nargs="*", choices=STATUSES)
    p.add_argument("--type", nargs="*", choices=TYPES)
    p.add_argument("--sprint", type=int)
    p.add_argument("--parent")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("plan", help="commit ready items to the next sprint")
    p.add_argument("--capacity", type=int, default=8)
    p.add_argument("--goal", default="")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("close-sprint", help="close the sprint and record the retro")
    p.add_argument("--went-well", nargs="*")
    p.add_argument("--improve", nargs="*")
    p.add_argument("--went-wrong", nargs="*")
    p.set_defaults(func=cmd_close_sprint)

    p = sub.add_parser("stats", help="counts plus the loop_done flag")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("gate", help="mechanical sprint sign-off check")
    p.add_argument("--sprint", type=int)
    p.set_defaults(func=cmd_gate)

    return parser


if __name__ == "__main__":
    parsed = build_parser().parse_args()
    parsed.func(parsed)
