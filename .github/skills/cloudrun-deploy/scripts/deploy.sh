#!/usr/bin/env bash
# Build, push and deploy both HotSpot Sentinels services to Cloud Run, then verify
# each one separately.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"

[[ -f .env ]] || { echo "No .env — run ./setup_gcp.sh first" >&2; exit 1; }
set -a; source .env; set +a

SERVICE="${SERVICE_NAME:-hotspot-backend}"
REGION="${GOOGLE_CLOUD_REGION:-asia-southeast1}"
PROJECT="${GOOGLE_CLOUD_PROJECT:?GOOGLE_CLOUD_PROJECT is not set in .env}"
REPO="hotspot"
TAG="$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d-%H%M%S)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${SERVICE}:${TAG}"

log() { printf '\n==> %s\n' "$1"; }

log "Target"
echo "  project : $PROJECT"
echo "  region  : $REGION"
echo "  service : $SERVICE"
echo "  image   : $IMAGE"

log "1/7 Artifact Registry repository"
if ! gcloud artifacts repositories describe "$REPO" --location="$REGION" --project="$PROJECT" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO" \
    --repository-format=docker --location="$REGION" --project="$PROJECT"
fi
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

log "2/7 Build backend (context = backend/ so the Dockerfile's COPY paths resolve)"
# Cloud Run only runs linux/amd64. Without this pin an Apple-silicon host pushes an
# arm64 image and the revision fails with "Container manifest type must support amd64/linux".
docker build --platform linux/amd64 -f backend/Dockerfile -t "$IMAGE" backend

log "3/7 Push backend"
docker push "$IMAGE"

log "4/7 Deploy backend"
# BIGQUERY_LOCATION is the one ratified exception to asia-southeast1: the NOAA GSOD
# public dataset is US multi-region and a cross-location job fails.
# GOOGLE_MAPS_API_KEY is mounted from Secret Manager, never --set-env-vars: an env var
# value is plainly readable by anyone holding run.services.get on the project.
MAPS_SECRET="${MAPS_SECRET_NAME:-hotspot-maps-api-key}"
if ! gcloud secrets describe "$MAPS_SECRET" --project "$PROJECT" >/dev/null 2>&1; then
  echo "Secret '${MAPS_SECRET}' does not exist — coordinate analysis would 502 in production." >&2
  echo "Create it once, piping the value on stdin so it never enters argv or shell history:" >&2
  echo "  printf '%s' \"\$GOOGLE_MAPS_API_KEY\" | gcloud secrets create ${MAPS_SECRET} \\" >&2
  echo "    --data-file=- --replication-policy=user-managed --locations=${REGION} --project ${PROJECT}" >&2
  echo "  gcloud secrets add-iam-policy-binding ${MAPS_SECRET} --project ${PROJECT} \\" >&2
  echo "    --member=serviceAccount:hotspot-run@${PROJECT}.iam.gserviceaccount.com \\" >&2
  echo "    --role=roles/secretmanager.secretAccessor" >&2
  exit 1
fi
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --port 8080 \
  --service-account "${RUNTIME_SERVICE_ACCOUNT:-hotspot-run@${PROJECT}.iam.gserviceaccount.com}" \
  --set-env-vars "^@^GOOGLE_CLOUD_PROJECT=${PROJECT}@GOOGLE_CLOUD_REGION=${REGION}@GCS_BUCKET_NAME=${GCS_BUCKET_NAME}@PUBSUB_TOPIC_ID=${PUBSUB_TOPIC_ID}@MODEL_ID=${MODEL_ID}@ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-http://localhost:8501}@BIGQUERY_LOCATION=${BIGQUERY_LOCATION:-US}@GOOGLE_MAPS_REQUEST_LIMIT=${GOOGLE_MAPS_REQUEST_LIMIT:-100}@GOOGLE_MAPS_REQUEST_WINDOW_SECONDS=${GOOGLE_MAPS_REQUEST_WINDOW_SECONDS:-3600}" \
  --set-secrets "GOOGLE_MAPS_API_KEY=${MAPS_SECRET}:latest" \
  "$@"

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" --format='value(status.url)')"
REVISION="$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" --format='value(status.latestReadyRevisionName)')"

log "5/7 Verify backend"
if curl -fsS "${URL}/api/health" >/dev/null; then
  echo "backend health OK"
else
  echo "BACKEND HEALTH CHECK FAILED — recent logs:" >&2
  gcloud run services logs read "$SERVICE" --region "$REGION" --project "$PROJECT" --limit 30 >&2 || true
  exit 1
fi

# The frontend is deployed and verified separately and on purpose. BUG-026 hid for
# three sprints because every container proof targeted the backend only, while the
# deployed dashboard was down: buildpacks had booted Streamlit under gunicorn and
# streamlit was not even installed.
log "6/7 Build, push and deploy frontend"
FRONTEND_SERVICE="${FRONTEND_SERVICE_NAME:-hotspot-frontend}"
FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${FRONTEND_SERVICE}:${TAG}"
docker build --platform linux/amd64 -f frontend/Dockerfile -t "$FRONTEND_IMAGE" frontend
docker push "$FRONTEND_IMAGE"
gcloud run deploy "$FRONTEND_SERVICE" \
  --image "$FRONTEND_IMAGE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --port 8080 \
  --set-env-vars "API_BASE_URL=${URL}"

FRONTEND_URL="$(gcloud run services describe "$FRONTEND_SERVICE" --region "$REGION" --project "$PROJECT" --format='value(status.url)')"
FRONTEND_REVISION="$(gcloud run services describe "$FRONTEND_SERVICE" --region "$REGION" --project "$PROJECT" --format='value(status.latestReadyRevisionName)')"

log "7/7 Verify frontend"
if curl -fsS "${FRONTEND_URL}/_stcore/health" >/dev/null; then
  echo "frontend health OK"
else
  echo "FRONTEND HEALTH CHECK FAILED — recent logs:" >&2
  gcloud run services logs read "$FRONTEND_SERVICE" --region "$REGION" --project "$PROJECT" --limit 30 >&2 || true
  exit 1
fi

printf '\nDEPLOYED\n  backend  : %s\n             revision %s\n             image    %s\n  frontend : %s\n             revision %s\n             image    %s\n' \
  "$URL" "$REVISION" "$IMAGE" "$FRONTEND_URL" "$FRONTEND_REVISION" "$FRONTEND_IMAGE"
