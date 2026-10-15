#!/usr/bin/env bash
# Manage the public alert wall during a demo recording.
#
# Rehearsals publish CRITICAL alerts, so the wall accumulates duplicates of the
# same zone. Clearing it before a take lets the recorded analysis be the alert
# that appears live.
#
# Deletes are permanent, so every destructive command writes a JSON backup first
# and `restore` puts those documents back.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
BACKUP_DIR="$ROOT/.alert-backups"
PROJECT="${GOOGLE_CLOUD_PROJECT:-hotspot-sentinels-7364}"
WALL_URL="https://hotspot-sentinels-7364.web.app"

usage() {
  cat <<'USAGE'
Manage the HotSpot Sentinels public alert wall.

  ./scripts/alert_wall.sh list              show every alert, newest first
  ./scripts/alert_wall.sh clear             delete all alerts (backed up first)
  ./scripts/alert_wall.sh keep N            keep the N newest, delete the rest
  ./scripts/alert_wall.sh oldest N          delete the N oldest
  ./scripts/alert_wall.sh dedupe            keep the newest per zone name
  ./scripts/alert_wall.sh restore [FILE]    restore from a backup (default: latest)

Options:
  -y, --yes    skip the confirmation prompt

Before recording, `clear` gives an empty wall so the alert you publish on camera
is visibly the first one. If the recorded run fails, `restore` puts the previous
alerts back.
USAGE
}

confirm() {
  [[ "${ASSUME_YES:-0}" == "1" ]] && return 0
  read -r -p "$1 [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]]
}

require_python() {
  [[ -x "$PYTHON" ]] || { echo "error: no interpreter at $PYTHON (set PYTHON=...)" >&2; exit 1; }
}

# Runs a mode inside Python because Firestore has no bulk delete-by-query in gcloud.
run_python() {
  "$PYTHON" - "$@" <<'PY'
import json, os, sys, datetime
from pathlib import Path
from google.cloud import firestore

mode, arg, backup_dir, project = sys.argv[1], sys.argv[2], Path(sys.argv[3]), sys.argv[4]
db = firestore.Client(project=project)
collection = db.collection("public_alerts")


def sort_key(pair):
    return str(pair[1].get("detected_at") or "")


docs = sorted(((d.id, d.to_dict()) for d in collection.stream()), key=sort_key, reverse=True)


def show(rows):
    if not rows:
        print("  (wall is empty)")
        return
    for doc_id, rec in rows:
        coords = rec.get("coordinates") or {}
        print(f"  {rec.get('hvi_score')}  {str(rec.get('zone_name'))[:38]:40}"
              f" {coords.get('lat')}, {coords.get('lng')}   {rec.get('detected_at')}")


def jsonable(value):
    return value.isoformat() if isinstance(value, datetime.datetime) else value


def back_up(rows):
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = backup_dir / f"alerts-{stamp}.json"
    path.write_text(json.dumps(
        [{k: jsonable(v) for k, v in rec.items()} for _, rec in rows], indent=2))
    print(f"  backed up {len(rows)} alert(s) to {path.name}")


def delete(rows):
    if not rows:
        print("  nothing to delete")
        return
    back_up(rows)
    for doc_id, _ in rows:
        collection.document(doc_id).delete()
    print(f"  deleted {len(rows)} alert(s)")


if mode == "list":
    print(f"{len(docs)} alert(s), newest first:")
    show(docs)

elif mode == "clear":
    delete(docs)

elif mode == "keep":
    delete(docs[int(arg):])

elif mode == "oldest":
    delete(docs[-int(arg):] if int(arg) else [])

elif mode == "dedupe":
    seen, doomed = set(), []
    for pair in docs:
        name = pair[1].get("zone_name")
        doomed.append(pair) if name in seen else seen.add(name)
    delete(doomed)

elif mode == "restore":
    source = Path(arg)
    records = json.loads(source.read_text())
    for record in records:
        # Back to a real timestamp, or the wall renders every card as "just now".
        stamp = record.get("detected_at")
        if isinstance(stamp, str):
            try:
                record["detected_at"] = datetime.datetime.fromisoformat(stamp)
            except ValueError:
                record["detected_at"] = firestore.SERVER_TIMESTAMP
        collection.document().set(record)
    print(f"  restored {len(records)} alert(s) from {source.name}")

remaining = len(list(collection.stream()))
print(f"  wall now holds {remaining} alert(s)")
PY
}

ASSUME_YES=0
args=()
for arg in "$@"; do
  case "$arg" in
    -y|--yes) ASSUME_YES=1 ;;
    -h|--help) usage; exit 0 ;;
    *) args+=("$arg") ;;
  esac
done
set -- "${args[@]:-}"

command="${1:-list}"
require_python

case "$command" in
  list)
    run_python list "" "$BACKUP_DIR" "$PROJECT"
    ;;
  clear)
    confirm "Delete every alert on the public wall?" || { echo "  cancelled"; exit 0; }
    run_python clear "" "$BACKUP_DIR" "$PROJECT"
    echo "  wall: $WALL_URL"
    ;;
  keep|oldest)
    [[ "${2:-}" =~ ^[0-9]+$ ]] || { echo "error: $command needs a number, e.g. $command 3" >&2; exit 1; }
    confirm "Run '$command $2' against the public wall?" || { echo "  cancelled"; exit 0; }
    run_python "$command" "$2" "$BACKUP_DIR" "$PROJECT"
    ;;
  dedupe)
    confirm "Keep only the newest alert per zone?" || { echo "  cancelled"; exit 0; }
    run_python dedupe "" "$BACKUP_DIR" "$PROJECT"
    ;;
  restore)
    file="${2:-}"
    if [[ -z "$file" ]]; then
      file="$(ls -t "$BACKUP_DIR"/alerts-*.json 2>/dev/null | head -1 || true)"
      [[ -n "$file" ]] || { echo "error: no backups in $BACKUP_DIR" >&2; exit 1; }
    fi
    confirm "Restore alerts from $(basename "$file")?" || { echo "  cancelled"; exit 0; }
    run_python restore "$file" "$BACKUP_DIR" "$PROJECT"
    ;;
  *)
    usage
    exit 1
    ;;
esac
