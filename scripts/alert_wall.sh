#!/usr/bin/env bash
# Manage the public alert wall during a demo recording.
#
# Rehearsals publish CRITICAL alerts, so the wall accumulates duplicates of the
# same zone. Clearing it before a take lets the recorded analysis be the alert
# that appears live.
#
# Deletes are permanent, so every option that removes alerts writes a JSON backup
# first, and the restore option puts those documents back.
#
# Run it with no arguments and pick from the menu.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
BACKUP_DIR="$ROOT/.alert-backups"
PROJECT="${GOOGLE_CLOUD_PROJECT:-hotspot-sentinels-7364}"
WALL_URL="https://hotspot-sentinels-7364.web.app"

print_menu() {
  cat <<'MENU'

  1  Show the alerts on the wall
  2  Clear the wall completely          (do this before a take)
  3  Keep only the newest few
  4  Delete the oldest few
  5  Keep one alert per zone
  6  Restore alerts from a backup
  q  Quit

MENU
}

confirm() {
  local reply
  read -r -p "  $1 [y/N] " reply || return 1
  [[ "$reply" =~ ^[Yy]$ ]]
}

# Sets COUNT. Fails on anything that is not a plain number, so a stray keystroke
# cannot turn into a delete of the wrong size.
ask_count() {
  local reply
  read -r -p "  $1 " reply || return 1
  if [[ ! "$reply" =~ ^[0-9]+$ ]]; then
    echo "  '$reply' is not a number — nothing done"
    return 1
  fi
  COUNT="$reply"
}

# Sets BACKUP_FILE from the snapshots on disk, newest first.
pick_backup() {
  local files=() file reply index=1
  while IFS= read -r file; do
    files+=("$file")
  done < <(ls -t "$BACKUP_DIR"/alerts-*.json 2>/dev/null || true)

  if [[ ${#files[@]} -eq 0 ]]; then
    echo "  no backups yet — one is written automatically before anything is deleted"
    return 1
  fi

  echo "  backups, newest first:"
  for file in "${files[@]}"; do
    printf "    %d  %s  (%s alerts)\n" "$index" "$(basename "$file")" \
      "$(grep -c '"hvi_score"' "$file" || true)"
    index=$((index + 1))
  done

  read -r -p "  which one? [1] " reply || return 1
  reply="${reply:-1}"
  if [[ ! "$reply" =~ ^[0-9]+$ ]] || [[ "$reply" -lt 1 ]] || [[ "$reply" -gt ${#files[@]} ]]; then
    echo "  no such backup — nothing done"
    return 1
  fi
  BACKUP_FILE="${files[$((reply - 1))]}"
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

require_python
[[ -t 0 ]] || { echo "error: this script is interactive — run it from a terminal" >&2; exit 1; }

echo "Public alert wall — $WALL_URL"
run_python list "" "$BACKUP_DIR" "$PROJECT"

while true; do
  print_menu
  read -r choice || { echo; break; }

  case "${choice:-}" in
    1)
      run_python list "" "$BACKUP_DIR" "$PROJECT"
      ;;
    2)
      if confirm "Delete EVERY alert on the public wall?"; then
        run_python clear "" "$BACKUP_DIR" "$PROJECT"
      else
        echo "  cancelled"
      fi
      ;;
    3)
      if ask_count "How many of the newest should stay?"; then
        if confirm "Keep the $COUNT newest and delete the rest?"; then
          run_python keep "$COUNT" "$BACKUP_DIR" "$PROJECT"
        else
          echo "  cancelled"
        fi
      fi
      ;;
    4)
      if ask_count "How many of the oldest should go?"; then
        if confirm "Delete the $COUNT oldest?"; then
          run_python oldest "$COUNT" "$BACKUP_DIR" "$PROJECT"
        else
          echo "  cancelled"
        fi
      fi
      ;;
    5)
      if confirm "Keep only the newest alert per zone?"; then
        run_python dedupe "" "$BACKUP_DIR" "$PROJECT"
      else
        echo "  cancelled"
      fi
      ;;
    6)
      if pick_backup && confirm "Restore from $(basename "$BACKUP_FILE")?"; then
        run_python restore "$BACKUP_FILE" "$BACKUP_DIR" "$PROJECT"
      fi
      ;;
    q|Q|quit|exit)
      break
      ;;
    "")
      ;;
    *)
      echo "  '$choice' is not an option — pick 1-6 or q"
      ;;
  esac
done

echo "  wall: $WALL_URL"
