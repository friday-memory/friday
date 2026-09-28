#!/usr/bin/env bash
# Deploy a NEW private service from a prebuilt linux/amd64 image digest.
set -euo pipefail
: "${PROJECT_AUTHORITY_CONFIRMED:?Set true after owner/repository authority is resolved}"
[[ "$PROJECT_AUTHORITY_CONFIRMED" == true ]]
: "${FREE_TIER_REVIEWED:?Confirm current account allowances before provisioning}"
[[ "$FREE_TIER_REVIEWED" == true ]]
: "${GCP_PROJECT:?}" "${GCP_REGION:?}" "${FRIDAY_IMAGE:?Use immutable image@sha256 digest}"
: "${FRIDAY_RUN_SERVICE_ACCOUNT:?}" "${TURSO_DATABASE_URL:?}"
: "${FRIDAY_KEY_SECRET:?Use secret-name:version}" "${TURSO_TOKEN_SECRET:?Use secret-name:version}"
[[ "$FRIDAY_IMAGE" == *@sha256:* ]]
service=friday-serverless-preview
mode=${1:-preview}
[[ "$mode" == preview || "$mode" == deploy-new ]]
args=(run deploy "$service" --project "$GCP_PROJECT" --region "$GCP_REGION"
  --image "$FRIDAY_IMAGE" --service-account "$FRIDAY_RUN_SERVICE_ACCOUNT"
  --no-allow-unauthenticated --invoker-iam-check --min 0 --min-instances 0
  --max 2 --max-instances 2 --cpu 1 --memory 512Mi --concurrency 8
  --cpu-throttling --no-cpu-boost --timeout 120 --port 8080
  --set-env-vars "FRIDAY_STORAGE_BACKEND=turso,TURSO_DATABASE_URL=$TURSO_DATABASE_URL"
  --set-secrets "FRIDAY_API_KEY=$FRIDAY_KEY_SECRET,TURSO_AUTH_TOKEN=$TURSO_TOKEN_SECRET")
if [[ "$mode" == preview ]]; then
  printf '%q ' gcloud "${args[@]}"
  printf '\n'
  exit 0
fi
[[ -n "$(gcloud auth list --filter=status:ACTIVE --format='value(account)')" ]]
# A list failure aborts; it is never interpreted as service absence.
services=$(gcloud run services list --project "$GCP_PROJECT" --region "$GCP_REGION" --format='value(metadata.name)')
if grep -Fxq "$service" <<< "$services"; then
  echo 'Refusing to overwrite an existing service; inspect its authority first.' >&2
  exit 1
fi
gcloud "${args[@]}"
