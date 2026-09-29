"""Run a command with private JSON credentials, without shell interpolation."""

import argparse
import json
import os
import stat
import subprocess
from pathlib import Path


def main():
    """Require a private credential file and pass values only via environment."""
    p = argparse.ArgumentParser()
    p.add_argument("config", type=Path)
    p.add_argument("command", nargs=argparse.REMAINDER)
    args = p.parse_args()
    if stat.S_IMODE(args.config.stat().st_mode) & 0o077:
        raise SystemExit("Config permissions must be 0600")
    values = json.loads(args.config.read_text())
    allowed = {
        "FRIDAY_STORAGE_BACKEND",
        "TURSO_DATABASE_URL",
        "TURSO_AUTH_TOKEN",
        "FRIDAY_API_KEY",
        "FRIDAY_URL",
        "FRIDAY_LOCAL_DB",
        "FRIDAY_GCP_IAM",
        "FRIDAY_GCLOUD",
        "CLOUDSDK_PYTHON",
        "FRIDAY_SOURCE_URL",
        "FRIDAY_SOURCE_API_KEY",
        "FRIDAY_QUALIFICATION_EVIDENCE",
        "FRIDAY_TEST_DATABASE_MARKER",
        "FRIDAY_GCP_PROJECT",
        "FRIDAY_GCP_REGION",
        "FRIDAY_CLOUD_RUN_SERVICE",
        "FRIDAY_ARTIFACT_REPOSITORY",
        "FRIDAY_CLOUD_RUN_JOB",
        "FRIDAY_CLOUD_SCHEDULER_JOB",
        "FRIDAY_GCP_RUNTIME_ACCOUNT",
        "FRIDAY_GCP_SCHEDULER_ACCOUNT",
        "FRIDAY_GCP_BUILD_ACCOUNT",
        "FRIDAY_CONFIG_DIR",
        "FRIDAY_DEPLOYMENT_STATE",
    }
    if set(values) - allowed or not all(isinstance(v, str) for v in values.values()):
        raise SystemExit("Invalid config keys or values")
    raise SystemExit(subprocess.call(args.command, env=dict(os.environ, **values)))


if __name__ == "__main__":
    main()
