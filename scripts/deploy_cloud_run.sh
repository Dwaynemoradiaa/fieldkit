#!/usr/bin/env bash
# Explicitly run only after reading docs/DEPLOYMENT.md. This creates billable resources.
set -euo pipefail
: "${PROJECT_ID:?Set PROJECT_ID}"
: "${SERVICE_ACCOUNT:?Set SERVICE_ACCOUNT email}"
: "${QDRANT_URL:?Set persistent external QDRANT_URL}"
: "${GEMINI_SECRET:?Set the Secret Manager secret name for GEMINI_API_KEY}"
: "${WORKSPACE_SECRET:?Set the secret name containing WORKSPACE_KEYS JSON}"
: "${QDRANT_SECRET:?Set the secret name for QDRANT_API_KEY}"
REGION="${REGION:-asia-south1}"
gcloud run deploy fieldkit \
  --project "$PROJECT_ID" --region "$REGION" --source . \
  --service-account "$SERVICE_ACCOUNT" --no-allow-unauthenticated \
  --memory 1Gi --cpu 1 --max-instances 1 --concurrency 4 --timeout 300 \
  --set-env-vars "ENVIRONMENT=production,AI_MODE=gemini,DATA_DIR=/tmp/fieldkit,QDRANT_URL=$QDRANT_URL" \
  --set-secrets "GEMINI_API_KEY=$GEMINI_SECRET:latest,WORKSPACE_KEYS=$WORKSPACE_SECRET:latest,QDRANT_API_KEY=$QDRANT_SECRET:latest"
