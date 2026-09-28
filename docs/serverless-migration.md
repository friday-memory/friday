# Parallel serverless migration

This is an opt-in gateway (`gateway.serverless:create_app`), not an in-place
conversion. The existing `gateway.main`, Compose deployment, source files,
volumes, client routing, and rollback host remain unchanged.

## Architecture and compatibility

`storage/base.py` defines the storage boundary. `storage/local.py` implements
transactional SQLite, while `storage/turso.py` uses the official `libsql` driver
against a remote libSQL URL with no replica file or silent local fallback.
Numbered SQL migrations create project-scoped durable records and a Porter FTS5
memory index. IDs, timestamps, supersession flags and legacy metadata survive
import unchanged. Facts, memories, state, blueprints, entities and edges all use
the selected database. Synchronous request handlers finish writes before replying.

Every data route requires an API key, including read endpoints. Keys in query
strings are rejected. `/health` exposes only availability. Cloud Run also requires
IAM; MCP can set `FRIDAY_GCP_IAM=true` and `FRIDAY_GCLOUD` to refresh an identity
token with the local gcloud session for each tool call. The API key goes in
`X-Friday-Key`; the IAM token goes in `X-Serverless-Authorization`. No client
configuration is changed by these scripts.

All candidate data APIs require a project. MCP defaults omitted projects to
`default`. Legacy unscoped facts/blueprints are explicitly enveloped under
`__legacy_unscoped__`; their source payloads are not rewritten or leaked into
other namespaces. An owner may later authorize a project mapping. This is one
shared-owner API key, not a multi-tenant authorization boundary.

Keyword search preserves the deployed SQLite FTS5 backend; this does not claim
semantic/vector parity with upstream Mem0. The candidate preserves the live
SQLite memory add/search/update/delete/supersede APIs and adds durable state,
graph creation/listing, blueprint listing and consolidation. The upstream Studio,
SDK-wide compatibility, graph rename/delete, automatic LLM graph extraction and
legacy persona file formats have not been qualified for this opt-in gateway.

## Private snapshot and migration

Run from an isolated checkout on the source host; do not SSH back into it.

```bash
python scripts/migration/export_current_state.py --output "$HOME/friday-migration-data"
python scripts/migration/import_to_turso.py --source "$HOME/friday-migration-data" --dry-run
```

The exporter uses a read-only SQLite transaction in the live container (including
WAL-visible records), never a raw copy of a changing database file. It refuses to
overwrite snapshots, writes private files outside Git and detects concurrent JSON
changes. It is specific to the inspected SQLite deployment; graph absence is
recorded because that deployment has no graph store. It does not export Neo4j.
It is not a cross-store atomic snapshot: repeat into a new directory during an
owner-authorized quiet period before eventual cutover. A copied snapshot alone
cannot capture subsequent source writes.

Credentials belong in a 0600 JSON file inside a 0700 private directory. Supported
keys are listed in `scripts/migration/with_config.py`. Never paste credentials
into command arguments, Git, logs or a PR.

```bash
python scripts/migration/with_config.py "$HOME/.config/friday-migration/prod.json" \
  python scripts/migration/import_to_turso.py --source "$HOME/friday-migration-data" --apply --initialize-schema
python scripts/migration/with_config.py "$HOME/.config/friday-migration/prod.json" \
  python scripts/migration/import_to_turso.py --source "$HOME/friday-migration-data" --verify
```

Initialize schema only on the dedicated new destination. An offline dry run
validates source hashes/counts/identities but explicitly does not check destination
conflicts. Use `--dry-run --check-destination` after schema initialization. Apply
always rechecks destination conflicts in its write transaction. Conflicting data
aborts the entire batch; identical reruns insert zero records. This is an initial
snapshot importer, not an incremental conflict-resolution system. Retain source
exports privately and plan reconciliation before cutover or rollback after new
writes have reached the target.

## Qualification

```bash
python -m pytest tests -q
ruff check .
python scripts/migration/with_config.py "$HOME/.config/friday-migration/test.json" \
  python scripts/qualification/remote_storage.py
python scripts/migration/with_config.py "$HOME/.config/friday-migration/prod.json" \
  python scripts/qualification/compare_backends.py --source "$HOME/friday-migration-data"
python scripts/migration/with_config.py "$HOME/.config/friday-migration/test.json" \
  python scripts/qualification/mcp_e2e.py
```

Remote fixture writes are restricted to the dedicated `friday-migration-test`
database and unique qualification namespaces. Production comparison is read-only.
Reports contain counts/pass-fail, never memory content. Parity checks exact source
payloads and sampled keyword result sets; it does not prove all possible search
queries or live concurrent-update parity. Unit fixtures exercise both SQLite and
native libSQL, including concurrent deduplication and import conflict rollback.

Build the separate `Dockerfile.serverless` image and run it on an unoccupied
loopback port with private credentials and no production mounts. Oracle is ARM;
Cloud Run requires a separately built `linux/amd64` image. Do not upload an ARM
image as the Cloud Run deployment artifact. Both builds need qualification.

## Cloud deployment and schedule

`scripts/deploy/cloud-run.sh preview` renders the exact command using explicitly
provided project, region, service-account, image digest and Secret Manager version
references. `deploy-new` refuses to overwrite an existing service. Service:
`friday-serverless-preview`, minimum 0, maximum 2, request-based CPU billing,
no CPU boost, IAM invocation required. No secrets are echoed.

`scripts/deploy/cloud-scheduler.sh` creates a distinct Cloud Run Job and a daily
03:00 UTC schedule. Scheduler uses OAuth to invoke the Jobs API; only the job's
runtime service account accesses its Turso secret. No Friday API key appears in
Scheduler headers, job descriptions, or command arguments. Existing jobs/schedules
are not silently updated. Provision dedicated service accounts and least-privilege
Secret Manager access only after confirming project and free-tier authority.

The scripts require `PROJECT_AUTHORITY_CONFIRMED=true` and
`FREE_TIER_REVIEWED=true`. Review current *account-wide* Cloud Run, Scheduler,
Artifact Registry and Secret Manager allowances before running. Scale-to-zero
and bounded instances are not spending caps. Do not upgrade Turso or enable
overages. If a paid resource is required, stop for owner direction.

No Cloud Run readiness claim is valid until its anonymous requests are rejected,
MCP writes reach Turso, and later/new Cloud Run instances read persisted facts,
memories, state, blueprints and graph records. Container recreation locally is
useful evidence but is not Cloud Run scale-to-zero evidence.

## Rollback and review

Keep Oracle running. Cutover and rollback change only the client URL/auth setup
once explicitly authorized. Before switching, reconcile writes since the snapshot;
after switching, target-only writes need preservation before rolling back.
Never stop containers, delete volumes, repoint clients, or decommission Oracle as
part of development. Open a PR for review; do not merge or cut over automatically.

References: [official libSQL Python access](https://docs.turso.tech/sdk/python/quickstart),
[Cloud Run deploy flags](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy),
[authenticated scheduled jobs](https://cloud.google.com/run/docs/triggering/using-scheduler),
[Turso pricing](https://turso.tech/pricing).

## Execution evidence (2026-09-28)

The Oracle deployment is a dirty SQLite checkout at upstream commit
`124bf3c346cf9525bd144254b50f5037c14c88e4`, with a healthy loopback service on
port 18000. No Neo4j container was present. Development used an independent clone
on `feat/serverless-turso-migration`, advanced to current upstream
`1ed3ddb` before implementing the opt-in backend.

The private snapshot contains 3 unscoped facts, 146 memories (140 active), and
1 unscoped blueprint. No graph or cognitive-state source exists in the deployed
SQLite implementation. The snapshot payload digest is
`2d0527cbb79b28e6faaa87b51f13b43be1f576405de9cdf3b5d7ed8bddf828ca`.
No memory content or credentials are included in this repository.

Turso's authenticated free plan had overages disabled. Dedicated libSQL databases
`friday-migration-test` and `friday-prod` were created with 256 MB limits. The
production-copy dry run had zero invalid records/conflicts; 150 records imported,
verification matched exact payloads, and a second apply inserted zero records.

Local SQLite and native libSQL qualification passes, as does direct remote Turso
qualification. The separately built ARM container on loopback port 18080 uses
only the test database and a read-only container filesystem. The four MCP tools
pass through that running container with remote writes verified. Anonymous GET
and POST probes of the six requested private routes return 401. Fixture hashes
for facts, memories, state, blueprints and graph data survive a candidate restart.

Seventy sampled queries match the reconstructed source index. Against the actual
running Oracle service, 67/70 have identical top-five result sets; the remaining
three differ at equal-score cutoff ties. The candidate uses deterministic ID
ordering for ties; the live service uses implicit insertion order. The comparison
tool separately verifies equivalent scores and that no better result was omitted.
This evidence does not establish semantic retrieval or exact tied-ID ordering.

## GCP continuation (2026-09-28)

The prior authentication blocker was stale. Bounded CLI checks confirm the
existing owner session, project `gen-lang-client-0381797315` (Friday Memory),
region `us-west1`, and enabled billing. Turso and GitHub sessions also pass.
Draft PR: https://github.com/friday-memory/friday/pull/6.

The owner explicitly authorized registry provisioning, Secret Manager, Cloud Run
and authenticated Scheduler in this project. `scripts/deploy/gcp_candidate.py`
implements that continuation. It uploads only a Git archive, builds linux/amd64,
smokes imports as the image's non-root user on a read-only filesystem, and deploys
an immutable digest. Secrets are read from private 0600 config files and sent to
Secret Manager over stdin; logs contain no secret values. Private resumable state
is kept at `~/.config/friday-migration/cloud.json`.

Commands (from the migration checkout):

```bash
python3 scripts/deploy/gcp_candidate.py provision
python3 scripts/deploy/gcp_candidate.py build
python3 scripts/deploy/gcp_candidate.py build-status
python3 scripts/deploy/gcp_candidate.py deploy --source test
.venv-migration/bin/python scripts/migration/with_config.py ~/.config/friday-migration/cloud-test.json .venv-migration/bin/python scripts/qualification/candidate_http.py --evidence ~/friday-migration-data/cloud-persistence.json
.venv-migration/bin/python scripts/migration/with_config.py ~/.config/friday-migration/cloud-test.json .venv-migration/bin/python scripts/qualification/mcp_e2e.py
python3 scripts/deploy/gcp_candidate.py replace --source test
.venv-migration/bin/python scripts/migration/with_config.py ~/.config/friday-migration/cloud-test.json .venv-migration/bin/python scripts/qualification/candidate_http.py --evidence ~/friday-migration-data/cloud-persistence.json --verify
python3 scripts/deploy/gcp_candidate.py replace --source prod
.venv-migration/bin/python scripts/migration/with_config.py ~/.config/friday-migration/cloud-prod.json .venv-migration/bin/python scripts/qualification/cloud_parity.py
```

Only after smoke/security/persistence checks pass, create the schedule using the
test database, trigger it via Cloud Scheduler, verify successful execution and
its durable consolidation results, then select the production database:

```bash
python3 scripts/deploy/gcp_candidate.py scheduler --source test
python3 scripts/deploy/gcp_candidate.py scheduler-run
python3 scripts/deploy/gcp_candidate.py scheduler-status
python3 scripts/deploy/gcp_candidate.py scheduler-target --source prod
python3 scripts/deploy/gcp_candidate.py inspect
```

A fresh revision provides a new container filesystem; compare saved API response
hashes across distinct ready revision names and read the same records directly
from remote Turso. This proves independence from the previous instance filesystem;
it does not claim an observed idle scale-to-zero event. Cloud Run has min 0,
max 2, request-based billing, no volume mounts and IAM invocation enforced.

Pricing references reviewed: [Cloud Run](https://cloud.google.com/run/pricing),
[Artifact Registry](https://cloud.google.com/artifact-registry/pricing),
[Secret Manager](https://cloud.google.com/secret-manager/pricing), and
[Cloud Build](https://cloud.google.com/build/pricing). Account-wide remaining
free allowances are not measurable from these deployment checks; no zero-cost
claim or spending cap is implied by the configured limits.

No client cutover or Oracle decommission is authorized by these commands.
Check for source writes again immediately before an owner-approved cutover.
