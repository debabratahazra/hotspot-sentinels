#!/usr/bin/env bash
# End-to-end local smoke test: seed imagery, start the API, exercise every route, validate the payload.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"

PORT="${PORT:-8080}"
BASE="http://127.0.0.1:${PORT}"
API_LOG="$(mktemp -t hotspot-api)"
ANALYZE_JSON="$(mktemp -t hotspot-analyze)"

log() { printf '\n==> %s\n' "$1"; }
fail() { printf '\nFAIL: %s\n' "$1" >&2; exit 1; }

[[ -f .env ]] || fail "No .env — run ./setup_gcp.sh first"
[[ -d venv ]] && source venv/bin/activate

log "1/6 Environment"
python3 .github/skills/gcp-environment-doctor/scripts/doctor.py || fail "environment not ready"

log "2/6 Vertex AI connectivity"
python backend/verify_setup.py || fail "Vertex AI unreachable"

log "3/6 Sample imagery"
if [[ -z "$(ls -A data_samples/*.png 2>/dev/null || true)" ]]; then
  python backend/tools/seed_samples.py || fail "seed_samples failed"
fi
SAMPLE="$(ls data_samples/*.png | head -n 1)"
echo "using $SAMPLE"

log "4/6 Starting API on :$PORT"
( cd backend && exec uvicorn main:app --host 127.0.0.1 --port "$PORT" ) >"$API_LOG" 2>&1 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 30); do
  if curl -fsS "$BASE/api/health" >/dev/null 2>&1; then break; fi
  kill -0 "$API_PID" 2>/dev/null || { cat "$API_LOG"; fail "API process died on startup"; }
  sleep 1
done
curl -fsS "$BASE/api/health" >/dev/null || { cat "$API_LOG"; fail "/api/health never came up"; }
echo "health OK"

log "5/6 Exercising routes"
curl -fsS -X POST "$BASE/api/analyze" \
  -F "image=@${SAMPLE};type=image/png" \
  -F "ambient_temp=36.5" \
  -F "zone_name=Smoke Test Zone" \
  -o "$ANALYZE_JSON" || { cat "$API_LOG"; fail "POST /api/analyze failed"; }
echo "analyze OK"

curl -fsS "$BASE/api/scans?limit=5" >/dev/null || fail "GET /api/scans failed"
echo "scans OK"

echo "--- negative cases ---"
CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/api/analyze" \
  -F "image=@requirements.txt;type=text/plain" -F "ambient_temp=36.5")
[[ "$CODE" == "415" ]] || fail "expected 415 for a non-image upload, got $CODE"
echo "415 on wrong content type OK"

log "6/6 Contract validation"
python3 .github/skills/heat-report-validation/scripts/validate_report.py "$ANALYZE_JSON" || fail "payload breaks the contract"

printf '\nSMOKE TEST PASSED\n  report: %s\n  api log: %s\n' "$ANALYZE_JSON" "$API_LOG"
