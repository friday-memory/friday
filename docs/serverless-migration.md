# Optional serverless storage and migration

This is an opt-in gateway (`gateway.serverless:create_app`) and migration path. It does not replace the existing gateway, Compose deployment, client routing, or rollback process.

## Architecture and compatibility

`storage/base.py` defines the storage boundary. `storage/local.py` implements transactional SQLite, while `storage/turso.py` uses the `libsql` driver for remote libSQL transactions without a local replica or silent fallback. Numbered SQL migrations create project-scoped records and a Porter FTS5 memory index. IDs, timestamps, supersession flags, and legacy metadata are retained during import.

Every data route requires an API key, including reads. Query-string keys are rejected. `/health` exposes availability only. Cloud Run can additionally require IAM; the MCP client can refresh an identity token when `FRIDAY_GCP_IAM=true`. The API key is sent in `X-Friday-Key`, and the IAM token in `X-Serverless-Authorization`.

All data APIs require a project namespace. MCP defaults omitted projects to `default`. Legacy unscoped facts and blueprints are explicitly enveloped under `__legacy_unscoped__`. The shared API key is not a multi-tenant authorization boundary.

Keyword search uses SQLite FTS5 and does not claim semantic or vector parity with Mem0. The opt-in gateway supports the documented memory APIs plus durable state, graph records, blueprints, and consolidation. Studio-wide and SDK-wide compatibility, graph rename/delete, automatic LLM graph extraction, and legacy persona formats are not covered by this gateway.

## Migration workflow

The exporter reads the Friday SQLite layout inside a container using a read-only transaction, including WAL-visible rows. It reads associated JSON files twice to detect concurrent changes and refuses to overwrite an existing snapshot. This adapter does not export graph data. Use a new private export directory for each capture; a snapshot is not an atomic view across separate stores and must be reconciled before any cutover.

```bash
export FRIDAY_SOURCE_CONTAINER='<source-container>'
export FRIDAY_SOURCE_DATA_ROOT='<container-data-directory>'
export EXPORT_DIR='<private-export-directory>'
python scripts/migration/export_current_state.py \
  --container "$FRIDAY_SOURCE_CONTAINER" \
  --data-root "$FRIDAY_SOURCE_DATA_ROOT" \
  --output "$EXPORT_DIR"
python scripts/migration/import_to_turso.py --source "$EXPORT_DIR" --dry-run
```

Keep export data and configuration outside Git. Set `FRIDAY_CONFIG_DIR` to a private directory with mode `0700`; configuration files must have mode `0600`. `scripts/migration/with_config.py` accepts only an explicit allowlist of environment variables and passes them to the command without shell interpolation. Never put credentials in command arguments, logs, commits, or a pull request.

Initialize the schema only on a dedicated destination. An offline dry run validates source hashes, counts, and identities but does not check destination conflicts. After initializing the destination, use `--dry-run --check-destination`. Apply rechecks conflicts in its write transaction and aborts the full batch on conflict; identical reruns insert zero records. This is an initial snapshot importer, not an incremental conflict-resolution system.

## Qualification

Run unit qualification locally, then use a dedicated non-production database for remote fixture writes. Set `FRIDAY_TEST_DATABASE_MARKER` when the database URL does not contain the default `-test-` marker. The remote storage, MCP, candidate HTTP, and consolidation qualification scripts refuse to run against URLs that do not match the marker.

```bash
python -m pytest tests -q
ruff check .
python scripts/migration/with_config.py "$FRIDAY_CONFIG_DIR/test.json" \
  python scripts/qualification/remote_storage.py
python scripts/migration/with_config.py "$FRIDAY_CONFIG_DIR/test.json" \
  python scripts/qualification/mcp_e2e.py
python scripts/migration/with_config.py "$FRIDAY_CONFIG_DIR/test.json" \
  python scripts/qualification/candidate_http.py --evidence "$FRIDAY_QUALIFICATION_EVIDENCE"
python scripts/migration/with_config.py "$FRIDAY_CONFIG_DIR/prod.json" \
  python scripts/qualification/compare_backends.py --source "$EXPORT_DIR"
```

Production comparison is read-only. It requires a private source snapshot and configured source and candidate URLs and credentials. Set `FRIDAY_SOURCE_URL` and `FRIDAY_SOURCE_API_KEY` in the private config to compare against an existing read-only source service. Reports contain pass/fail status only; do not publish local qualification output or snapshot manifests.

```bash
python scripts/migration/with_config.py "$FRIDAY_CONFIG_DIR/prod.json" \
  python scripts/qualification/cloud_parity.py --source "$EXPORT_DIR"
```

## Cloud deployment

The Cloud Run and Scheduler scripts support preview and `deploy-new` modes. They require explicit deployment authority and cost review. Set project and region in the environment; the Cloud Run service defaults to `friday-serverless` and can be set with `FRIDAY_CLOUD_RUN_SERVICE`. Artifact repository, service-account IDs, job names, and scheduler name can be configured separately or derived from the service name.

```bash
export FRIDAY_GCP_PROJECT='<authorized-project-id>'
export FRIDAY_GCP_REGION='<region>'
export FRIDAY_CLOUD_RUN_SERVICE='friday-serverless'
export PROJECT_AUTHORITY_CONFIRMED=true
export FREE_TIER_REVIEWED=true
python scripts/deploy/gcp_candidate.py provision
python scripts/deploy/gcp_candidate.py build
python scripts/deploy/gcp_candidate.py build-status
python scripts/deploy/gcp_candidate.py deploy --source test
python scripts/deploy/gcp_candidate.py scheduler --source test
```

The deployment helper reads secrets from private configuration files and stores resumable state under `FRIDAY_CONFIG_DIR` unless `FRIDAY_DEPLOYMENT_STATE` is set. It uploads a Git archive, builds an immutable image, performs a non-root read-only image smoke check, and refuses to overwrite existing services, jobs, or schedules. Cloud Run uses IAM invocation, bounded instances, and request-based CPU billing. These settings are not spending caps; check current account-wide limits before provisioning and stop if paid resources or upgrades are required.

Scheduler uses OAuth to invoke the Cloud Run Jobs API. The job runtime identity reads its Turso token from Secret Manager; an application API key is not placed in Scheduler headers or arguments. Secret names and service-account emails are derived from configured inputs and are not included in this guide.

Do not cut over clients, delete source volumes, stop the source service, or decommission rollback resources as part of development. Before any owner-authorized cutover, capture and reconcile source writes since the snapshot. Reconcile destination-only writes before rollback.

References: [libSQL Python access](https://docs.turso.tech/sdk/python/quickstart), [Cloud Run deploy flags](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy), [authenticated scheduled jobs](https://cloud.google.com/run/docs/triggering/using-scheduler), and [Turso pricing](https://turso.tech/pricing).
