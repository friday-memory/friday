#!/usr/bin/env bash
# OAuth-authenticated Jobs API invocation; credentials remain in Secret Manager.
set -euo pipefail
: "${PROJECT_AUTHORITY_CONFIRMED:?}" "${FREE_TIER_REVIEWED:?}"
[[ "$PROJECT_AUTHORITY_CONFIRMED" == true && "$FREE_TIER_REVIEWED" == true ]]
: "${GCP_PROJECT:?}" "${GCP_REGION:?}" "${FRIDAY_IMAGE:?}"
: "${FRIDAY_RUN_SERVICE_ACCOUNT:?}" "${FRIDAY_SCHEDULER_SERVICE_ACCOUNT:?}"
: "${TURSO_DATABASE_URL:?}" "${TURSO_TOKEN_SECRET:?}"
mode=${1:-preview}
[[ "$mode" == preview || "$mode" == deploy-new ]]
job=friday-consolidation-preview
schedule=friday-daily-consolidation-preview
run=(run jobs deploy "$job" --project "$GCP_PROJECT" --region "$GCP_REGION"
 --image "$FRIDAY_IMAGE" --service-account "$FRIDAY_RUN_SERVICE_ACCOUNT"
 --tasks 1 --parallelism 1 --max-retries 1 --task-timeout 300s --cpu 1 --memory 512Mi
 --command python --args=-m,scripts.deploy.consolidate
 --set-env-vars "FRIDAY_STORAGE_BACKEND=turso,TURSO_DATABASE_URL=$TURSO_DATABASE_URL"
 --set-secrets "TURSO_AUTH_TOKEN=$TURSO_TOKEN_SECRET")
iam=(run jobs add-iam-policy-binding "$job" --project "$GCP_PROJECT" --region "$GCP_REGION"
 --member "serviceAccount:$FRIDAY_SCHEDULER_SERVICE_ACCOUNT" --role roles/run.invoker)
scheduler=(scheduler jobs create http "$schedule" --project "$GCP_PROJECT" --location "$GCP_REGION"
 --schedule '0 3 * * *' --time-zone UTC --http-method POST
 --uri "https://run.googleapis.com/v2/projects/$GCP_PROJECT/locations/$GCP_REGION/jobs/$job:run"
 --oauth-service-account-email "$FRIDAY_SCHEDULER_SERVICE_ACCOUNT"
 --headers Content-Type=application/json --message-body '{}')
if [[ "$mode" == preview ]]; then
 for name in run iam scheduler; do declare -n command_args="$name"; printf '%q ' gcloud "${command_args[@]}"; printf '\n'; done
 exit 0
fi
jobs=$(gcloud run jobs list --project "$GCP_PROJECT" --region "$GCP_REGION" --format='value(metadata.name)')
schedules=$(gcloud scheduler jobs list --project "$GCP_PROJECT" --location "$GCP_REGION" --format='value(name)')
if grep -Fxq "$job" <<< "$jobs" || grep -Fq "/jobs/$schedule" <<< "$schedules"; then
 echo 'Refusing to overwrite an existing job or schedule; inspect first.' >&2
 exit 1
fi
gcloud "${run[@]}"
gcloud "${iam[@]}"
gcloud "${scheduler[@]}"
