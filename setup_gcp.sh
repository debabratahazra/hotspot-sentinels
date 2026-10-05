#!/bin/zsh
# ==============================================================================
# HotSpot Sentinels - GCP Environment Setup & Login Automation
# Designed for macOS zsh in VS Code Terminal
# ==============================================================================

set -e # Exit immediately on error

echo "=========================================="
echo " Starting HotSpot Sentinels GCP Setup"
echo "=========================================="

# 1. Target Configurations
export REGION="${GOOGLE_CLOUD_REGION:-asia-southeast1}" # Singapore region (Hackathon finale host)
# Provision whatever topic the caller configured, so the created topic and the
# generated .env cannot disagree.
export PUBSUB_TOPIC="${PUBSUB_TOPIC_ID:-heat-resilience-alerts}"

# 2. Authenticate CLI & Application Default Credentials (ADC)
echo "\n[Step 1/5] Checking Authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "No active account found. Initiating gcloud login..."
    gcloud auth login
else
    echo "gcloud authenticated as: $(gcloud auth list --filter=status:ACTIVE --format='value(account)')"
fi

echo "Verifying Application Default Credentials (ADC)..."
gcloud auth application-default login

# 3. Project Discovery and Selection
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")

if [[ -z "$CURRENT_PROJECT" || "$CURRENT_PROJECT" == "(unset)" ]]; then
    echo "\n[Step 2/5] No project currently selected."
    echo "Available projects:"
    gcloud projects list --format="table(projectId,name)"
    echo -n "Enter the Project ID you created for HotSpot Sentinels: "
    read TARGET_PROJECT
    gcloud config set project "$TARGET_PROJECT"
    export PROJECT_ID="$TARGET_PROJECT"
else
    export PROJECT_ID="$CURRENT_PROJECT"
    echo "\n[Step 2/5] Current active project: $PROJECT_ID"
fi

export BUCKET_NAME="${PROJECT_ID}-data"

# 4. Ensure Essential APIs are Enabled
echo "\n[Step 3/5] Verifying and Enabling APIs..."
gcloud services enable \
    aiplatform.googleapis.com \
    run.googleapis.com \
    storage.googleapis.com \
    bigquery.googleapis.com \
    pubsub.googleapis.com \
    firestore.googleapis.com

# 5. Provision Storage, Pub/Sub & Firestore if missing
echo "\n[Step 4/5] Checking Core Cloud Resources..."

# Cloud Storage Bucket
if ! gcloud storage buckets describe gs://$BUCKET_NAME >/dev/null 2>&1; then
    echo "Creating Cloud Storage bucket: gs://$BUCKET_NAME..."
    gcloud storage buckets create gs://$BUCKET_NAME --location=$REGION
else
    echo "Cloud Storage bucket 'gs://$BUCKET_NAME' already exists."
fi

# Pub/Sub Topic
if ! gcloud pubsub topics describe $PUBSUB_TOPIC >/dev/null 2>&1; then
    echo "Creating Pub/Sub topic: $PUBSUB_TOPIC..."
    gcloud pubsub topics create $PUBSUB_TOPIC
else
    echo "Pub/Sub topic '$PUBSUB_TOPIC' already exists."
fi

# Firestore Database check
echo "Checking Firestore database state..."
gcloud firestore databases describe --format="value(name)" >/dev/null 2>&1 || {
    echo "Creating default Firestore native database..."
    gcloud firestore databases create --location=$REGION --type=firestore-native
}

# 6. Generate local .env file
echo "\n[Step 5/5] Generating local .env configuration..."
cat << EOF > .env
GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
GOOGLE_CLOUD_REGION=${REGION}
GCS_BUCKET_NAME=${BUCKET_NAME}
PUBSUB_TOPIC_ID=${PUBSUB_TOPIC}
GOOGLE_MAPS_API_KEY=
MODEL_ID=gemini-2.5-flash
ALLOWED_ORIGINS=http://localhost:8501
PORT=8080
# NOAA GSOD is a US multi-region dataset; this is the one ratified exception to
# asia-southeast1. Its absence made every climate query fail in BUG-025.
BIGQUERY_LOCATION=US
# Where the Streamlit dashboard looks for the backend when run locally.
API_BASE_URL=http://localhost:8080
# Per-process cache-miss budget for Maps imagery. Cache hits do not consume it.
GOOGLE_MAPS_REQUEST_LIMIT=100
GOOGLE_MAPS_REQUEST_WINDOW_SECONDS=3600
EOF

echo "\n=========================================="
echo " [SUCCESS] HotSpot Sentinels GCP Environment Configured"
echo " Project: $PROJECT_ID | Region: $REGION"
echo " Run 'python backend/verify_setup.py' to run end-to-end check."
echo "=========================================="
