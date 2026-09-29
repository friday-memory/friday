"""Bounded, resumable Friday-only GCP provisioning; never log credentials."""

import argparse
import json
import os
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = REGION = REPO = SERVICE = JOB = SCHEDULE = ""
RUNTIME = SCHEDULER = BUILD = ""
PRIVATE = Path()
STATE = Path()


def require_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Required environment variable is missing: {name}")
    return value


def configure():
    """Load deployment identity from the operator's environment."""
    global PROJECT, REGION, REPO, SERVICE, JOB, SCHEDULE
    global RUNTIME, SCHEDULER, BUILD, PRIVATE, STATE

    PROJECT = require_env("FRIDAY_GCP_PROJECT")
    REGION = require_env("FRIDAY_GCP_REGION")
    SERVICE = os.getenv("FRIDAY_CLOUD_RUN_SERVICE", "friday-serverless")
    REPO = os.getenv("FRIDAY_ARTIFACT_REPOSITORY", "friday")
    JOB = os.getenv("FRIDAY_CLOUD_RUN_JOB", f"{SERVICE}-consolidation")
    SCHEDULE = os.getenv("FRIDAY_CLOUD_SCHEDULER_JOB", f"{SERVICE}-daily-consolidation")
    RUNTIME = os.getenv("FRIDAY_GCP_RUNTIME_ACCOUNT", f"{SERVICE}-runtime")
    SCHEDULER = os.getenv("FRIDAY_GCP_SCHEDULER_ACCOUNT", f"{SERVICE}-scheduler")
    BUILD = os.getenv("FRIDAY_GCP_BUILD_ACCOUNT", f"{SERVICE}-build")
    if any(len(name) > 30 for name in (RUNTIME, SCHEDULER, BUILD)):
        raise SystemExit("Service-account IDs must be 30 characters or fewer")
    RUNTIME = f"{RUNTIME}@{PROJECT}.iam.gserviceaccount.com"
    SCHEDULER = f"{SCHEDULER}@{PROJECT}.iam.gserviceaccount.com"
    BUILD = f"{BUILD}@{PROJECT}.iam.gserviceaccount.com"
    PRIVATE = Path(os.getenv("FRIDAY_CONFIG_DIR", str(Path.home() / ".config/friday")))
    STATE = Path(os.getenv("FRIDAY_DEPLOYMENT_STATE", str(PRIVATE / "deployment.json")))


def secret_name(source, suffix):
    return f"{SERVICE}-{source}-{suffix}"


def gc(*args, data=None, timeout=90):
    result = subprocess.run(
        ["gcloud", *args, "--project", PROJECT, "--quiet", "--format=json"],
        input=data,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        # gcloud errors for these operations contain resource names, not secret payloads.
        if data is None:
            print(result.stderr.decode())
        raise RuntimeError(f"gcloud {args[0]} {args[1]} failed")
    return json.loads(result.stdout or "null")


def config(name):
    path = PRIVATE / f"{name}.json"
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("Private config permissions required")
    return json.loads(path.read_text())


def save(state):
    STATE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    STATE.parent.chmod(0o700)
    STATE.write_text(json.dumps(state, indent=2))
    STATE.chmod(0o600)


def provision(state):
    repositories = gc("artifacts", "repositories", "list", "--location", REGION)
    if not any(r["name"].endswith("/" + REPO) for r in repositories):
        gc(
            "artifacts",
            "repositories",
            "create",
            REPO,
            "--location",
            REGION,
            "--repository-format=docker",
            "--description=Friday migration candidate",
        )
    accounts = {a["email"] for a in gc("iam", "service-accounts", "list")}
    for email in (RUNTIME, SCHEDULER, BUILD):
        name = email.split("@", 1)[0]
        if email not in accounts:
            gc("iam", "service-accounts", "create", name)
    for role in (
        "roles/artifactregistry.writer",
        "roles/logging.logWriter",
        "roles/storage.objectViewer",
    ):
        gc(
            "projects",
            "add-iam-policy-binding",
            PROJECT,
            "--member",
            f"serviceAccount:{BUILD}",
            "--role",
            role,
            "--condition=None",
        )
    secrets = {s["name"].split("/")[-1] for s in gc("secrets", "list")}
    state.setdefault("secrets", {})
    for source in ("test", "prod"):
        values = config(source)
        for key, suffix in (("FRIDAY_API_KEY", "api-key"), ("TURSO_AUTH_TOKEN", "turso-token")):
            name = secret_name(source, suffix)
            if name not in secrets:
                gc(
                    "secrets",
                    "create",
                    name,
                    "--replication-policy=user-managed",
                    "--locations",
                    REGION,
                )
            if name not in state["secrets"]:
                version = gc(
                    "secrets", "versions", "add", name, "--data-file=-", data=values[key].encode()
                )
                state["secrets"][name] = version["name"].split("/")[-1]
                save(state)
            gc(
                "secrets",
                "add-iam-policy-binding",
                name,
                "--member",
                f"serviceAccount:{RUNTIME}",
                "--role=roles/secretmanager.secretAccessor",
                "--condition=None",
            )
    print("ARTIFACT_REGISTRY=READY\nSECRET_MANAGER=READY")


def build(state):
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    image = f"{REGION}-docker.pkg.dev/{PROJECT}/{REPO}/gateway:{sha}"
    # Only tracked files enter Cloud Build. Private files and local environments cannot enter the archive.
    with tempfile.TemporaryDirectory() as temp:
        archive = subprocess.check_output(["git", "archive", "HEAD"], cwd=ROOT)
        # Preserve Git modes despite the private credentials umask used by this process.
        subprocess.run(["tar", "-xp", "-C", temp], input=archive, check=True)
        spec = {
            "steps": [
                {
                    "name": "gcr.io/cloud-builders/docker",
                    "args": [
                        "build",
                        "--platform=linux/amd64",
                        "-f",
                        "Dockerfile.serverless",
                        "-t",
                        image,
                        ".",
                    ],
                },
                {
                    "name": "gcr.io/cloud-builders/docker",
                    "args": [
                        "run",
                        "--rm",
                        "--read-only",
                        "--network=none",
                        "--entrypoint=python",
                        image,
                        "-c",
                        "from gateway.serverless import create_app; from scripts.deploy.consolidate import main; print('AMD64_IMPORT_SMOKE=PASS')",
                    ],
                },
            ],
            "images": [image],
            "timeout": "1800s",
            "serviceAccount": f"projects/{PROJECT}/serviceAccounts/{BUILD}",
            "options": {"logging": "CLOUD_LOGGING_ONLY"},
        }
        path = Path(temp) / "cloudbuild.json"
        path.write_text(json.dumps(spec))
        result = gc(
            "builds",
            "submit",
            temp,
            "--config",
            str(path),
            "--region",
            REGION,
            "--default-buckets-behavior=regional-user-owned-bucket",
            "--async",
            timeout=180,
        )
        state.update(build_id=result["id"], image_tag=image)
        save(state)
        print("BUILD_ID=" + result["id"])


def build_status(state):
    result = gc("builds", "describe", state["build_id"], "--region", REGION)
    print("BUILD_STATUS=" + result["status"])
    if result["status"] == "SUCCESS":
        state["image"] = (
            state["image_tag"].rsplit(":", 1)[0] + "@" + result["results"]["images"][0]["digest"]
        )
        save(state)


def environment(state, source):
    values = config(source)
    return dict(
        os.environ,
        GCP_PROJECT=PROJECT,
        GCP_REGION=REGION,
        FRIDAY_CLOUD_RUN_SERVICE=SERVICE,
        FRIDAY_CLOUD_RUN_JOB=JOB,
        FRIDAY_CLOUD_SCHEDULER_JOB=SCHEDULE,
        PROJECT_AUTHORITY_CONFIRMED="true",
        FREE_TIER_REVIEWED="true",
        FRIDAY_IMAGE=state["image"],
        FRIDAY_RUN_SERVICE_ACCOUNT=RUNTIME,
        FRIDAY_SCHEDULER_SERVICE_ACCOUNT=SCHEDULER,
        TURSO_DATABASE_URL=values["TURSO_DATABASE_URL"],
        FRIDAY_KEY_SECRET=f"{secret_name(source, 'api-key')}:"
        + state["secrets"][secret_name(source, "api-key")],
        TURSO_TOKEN_SECRET=f"{secret_name(source, 'turso-token')}:"
        + state["secrets"][secret_name(source, "turso-token")],
    )


def deploy(state, source, replace=False):
    env = environment(state, source)
    if replace:
        gc(
            "run",
            "services",
            "update",
            SERVICE,
            "--region",
            REGION,
            "--image",
            state["image"],
            "--update-env-vars",
            f"TURSO_DATABASE_URL={env['TURSO_DATABASE_URL']},FRIDAY_QUALIFICATION_GENERATION={os.urandom(4).hex()}",
            "--set-secrets",
            f"FRIDAY_API_KEY={env['FRIDAY_KEY_SECRET']},TURSO_AUTH_TOKEN={env['TURSO_TOKEN_SECRET']}",
            timeout=300,
        )
    else:
        subprocess.run(
            ["bash", "scripts/deploy/cloud-run.sh", "deploy-new"],
            cwd=ROOT,
            env=env,
            check=True,
            timeout=300,
        )
    result = gc("run", "services", "describe", SERVICE, "--region", REGION)
    state.update(
        url=result["status"]["url"],
        revision=result["status"]["latestReadyRevisionName"],
        source=source,
    )
    save(state)
    write_client_config(state, source)
    print("CLOUD_RUN_REVISION=" + state["revision"] + "\nCLOUD_RUN_URL=" + state["url"])


def write_client_config(state, source):
    values = config(source)
    values.update(
        FRIDAY_URL=state["url"],
        FRIDAY_GCP_IAM="true",
        CLOUDSDK_PYTHON=str((ROOT / ".venv-migration/bin/python").resolve()),
        FRIDAY_GCLOUD="/usr/bin/gcloud",
    )
    path = PRIVATE / f"cloud-{source}.json"
    path.write_text(json.dumps(values))
    path.chmod(0o600)


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser()
    p.add_argument(
        "action",
        choices=[
            "provision",
            "build",
            "build-status",
            "deploy",
            "replace",
            "scheduler",
            "scheduler-run",
            "scheduler-status",
            "scheduler-target",
            "inspect",
            "client-config",
        ],
    )
    p.add_argument("--source", choices=["test", "prod"], default="test")
    args = p.parse_args()
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    if args.action == "client-config":
        write_client_config(state, args.source)
    elif args.action == "provision":
        provision(state)
    elif args.action == "build":
        build(state)
    elif args.action == "build-status":
        build_status(state)
    elif args.action in ("deploy", "replace"):
        deploy(state, args.source, args.action == "replace")
    elif args.action == "scheduler-run":
        state["scheduler_attempt"] = datetime.now(timezone.utc).isoformat()
        save(state)
        gc("scheduler", "jobs", "run", SCHEDULE, "--location", REGION)
        print("SCHEDULER_TRIGGER=ACCEPTED")
    elif args.action == "scheduler-status":
        schedule = gc(
            "scheduler",
            "jobs",
            "describe",
            SCHEDULE,
            "--location",
            REGION,
        )
        executions = gc(
            "run",
            "jobs",
            "executions",
            "list",
            "--job",
            JOB,
            "--region",
            REGION,
        )
        attempt = datetime.fromisoformat(state["scheduler_attempt"])
        recent = [
            e
            for e in executions
            if datetime.fromisoformat(e["metadata"]["creationTimestamp"].replace("Z", "+00:00"))
            >= attempt
        ]
        success = [
            e
            for e in recent
            if any(
                c["type"] == "Completed" and c["status"] == "True"
                for c in e.get("status", {}).get("conditions", [])
            )
        ]
        print("CLOUD_SCHEDULER_STATE=" + schedule["state"])
        print("SCHEDULER_STATUS_CODE=" + str(schedule.get("status", {}).get("code", 0)))
        print("CONSOLIDATION_JOB=" + ("PASS" if success else "PENDING_OR_FAILED"))
        if success:
            state["scheduler_execution"] = success[0]["metadata"]["name"]
            save(state)
            print("EXECUTION=" + state["scheduler_execution"])
    elif args.action == "scheduler-target":
        if not state.get("scheduler_execution"):
            raise ValueError("Qualification execution required")
        env = environment(state, args.source)
        gc(
            "run",
            "jobs",
            "update",
            JOB,
            "--region",
            REGION,
            "--set-env-vars",
            f"FRIDAY_STORAGE_BACKEND=turso,TURSO_DATABASE_URL={env['TURSO_DATABASE_URL']}",
            "--set-secrets",
            f"TURSO_AUTH_TOKEN={env['TURSO_TOKEN_SECRET']}",
            timeout=180,
        )
        print("SCHEDULER_TARGET=" + args.source)
    elif args.action == "inspect":
        service = gc("run", "services", "describe", SERVICE, "--region", REGION)
        template = service["spec"]["template"]
        print(
            json.dumps(
                {
                    "service": SERVICE,
                    "revision": service["status"]["latestReadyRevisionName"],
                    "url": service["status"]["url"],
                    "annotations": service["metadata"].get("annotations"),
                    "revision_annotations": template["metadata"].get("annotations"),
                    "volumes": template["spec"].get("volumes", []),
                    "traffic": service["status"].get("traffic"),
                }
            )
        )
        print(json.dumps(gc("run", "services", "get-iam-policy", SERVICE, "--region", REGION)))
    else:
        subprocess.run(
            ["bash", "scripts/deploy/cloud-scheduler.sh", "deploy-new"],
            cwd=ROOT,
            env=environment(state, args.source),
            check=True,
            timeout=300,
        )


if __name__ == "__main__":
    configure()
    main()
