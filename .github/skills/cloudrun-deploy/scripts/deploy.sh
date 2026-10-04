#!/usr/bin/env bash
# Build, push, and deploy the HotSpot Sentinels backend to Cloud Run, then verify it.
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

log "1/5 Artifact Registry repository"
if ! gcloud artifacts repositories describe "$REPO" --location="$REGION" --project="$PROJECT" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO" \
    --repository-format=docker --location="$REGION" --project="$PROJECT"
fi
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

log "2/5 Build (context = backend/ so the Dockerfile's COPY paths resolve)"
# Cloud Run only runs linux/amd64. Without this pin an Apple-silicon host pushes an
# arm64 image and the revision fails with "Container manifest type must support amd64/linux".
docker build --platform linux/amd64 -f backend/Dockerfile -t "$IMAGE" backend

log "3/5 Push"
docker push "$IMAGE"

log "4/5 Deploy"
# BIGQUERY_LOCATION is the one ratified exception to asia-southeast1: the NOAA GSOD
# public dataset is US multi-region and a cross-location job fails.
# GOOGLE_MAPS_API_KEY is injected at runtime only and never baked into the image.
: "${GOOGLE_MAPS_API_KEY:?GOOGLE_MAPS_API_KEY is not set in .env — coordinate analysis would 502 in production}"
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --port 8080 \
  --set-env-vars "^@^GOOGLE_CLOUD_PROJECT=${PROJECT}@GOOGLE_CLOUD_REGION=${REGION}@GCS_BUCKET_NAME=${GCS_BUCKET_NAME}@PUBSUB_TOPIC_ID=${PUBSUB_TOPIC_ID}@MODEL_ID=${MODEL_ID}@ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-http://localhost:8501}@BIGQUERY_LOCATION=${BIGQUERY_LOCATION:-US}@GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}@GOOGLE_MAPS_REQUEST_LIMIT=${GOOGLE_MAPS_REQUEST_LIMIT:-100}@GOOGLE_MAPS_REQUEST_WINDOW_SECONDS=${GOOGLE_MAPS_REQUEST_WINDOW_SECONDS:-3600}" \
  "$@"

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" --format='value(status.url)')"
REVISION="$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" --format='value(status.latestReadyRevisionName)')"

log "5/5 Verify"
if curl -fsS "${URL}/api/health" >/dev/null; then
  echo "health OK"
else
  echo "HEALTH CHECK FAILED — recent logs:" >&2
  gcloud run services logs read "$SERVICE" --region "$REGION" --project "$PROJECT" --limit 30 >&2 || true
  exit 1
fi

printf '\nDEPLOYED\n  url      : %s\n  revision : %s\n  image    : %s\n' "$URL" "$REVISION" "$IMAGE"
