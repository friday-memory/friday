"""Start a separate read-only candidate container with private credentials."""

import argparse
import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path


def main():
    """Pass secrets in a temporary mode-0600 file, never command arguments."""
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--image", required=True)
    args = p.parse_args()
    if stat.S_IMODE(args.config.stat().st_mode) & 0o077:
        raise SystemExit("Config must be private")
    values = json.loads(args.config.read_text())
    if "friday-migration-test-" not in values.get("TURSO_DATABASE_URL", ""):
        raise SystemExit("Candidate qualification requires the test database")
    fd, path = tempfile.mkstemp(prefix="friday-candidate-", suffix=".env")
    try:
        with os.fdopen(fd, "w") as f:
            for key in (
                "FRIDAY_STORAGE_BACKEND",
                "TURSO_DATABASE_URL",
                "TURSO_AUTH_TOKEN",
                "FRIDAY_API_KEY",
            ):
                value = values[key]
                if "\n" in value or "\r" in value:
                    raise ValueError("Invalid config value")
                f.write(key + "=" + value + "\n")
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                "friday-serverless-qualification",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--memory=512m",
                "--cpus=1",
                "--pids-limit=128",
                "-p",
                "127.0.0.1:18080:8080",
                "--env-file",
                path,
                args.image,
            ],
            check=True,
        )
    finally:
        os.unlink(path)


if __name__ == "__main__":
    main()
