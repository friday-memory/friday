"""Read-only Cloud Run / Turso / live Oracle comparison; output counts only."""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.migration.import_to_turso import read_snapshot
from scripts.qualification.compare_backends import equivalent_cutoff_ties
from storage import from_environment


def main():
    token = subprocess.check_output(
        ["gcloud", "auth", "print-identity-token"], text=True, timeout=30
    ).strip()
    key = dotenv_values(Path.home() / "friday-oracle-ops/secrets/friday.env")
    source_key = key.get("FRIDAY_API_KEY") or key.get("BRAIN_API_KEY")
    if not source_key:
        raise ValueError("Oracle key unavailable")
    records = read_snapshot(Path.home() / "friday-migration-data")
    db = from_environment()
    queries = exact = tied = 0
    with (
        httpx.Client(
            base_url=os.environ["FRIDAY_URL"],
            timeout=60,
            headers={
                "X-Friday-Key": os.environ["FRIDAY_API_KEY"],
                "X-Serverless-Authorization": "Bearer " + token,
            },
        ) as cloud,
        httpx.Client(
            base_url="http://127.0.0.1:18000", timeout=30, headers={"X-Friday-Key": source_key}
        ) as live,
    ):
        assert cloud.get("/health").status_code == live.get("/health").status_code == 200
        memories = [r for r in records if r.kind == "memories"]
        for project in sorted({r.project for r in memories}):
            tokens = sorted(
                {
                    t.lower()
                    for r in memories
                    if r.project == project
                    for t in re.findall(r"\w+", r.data["content"])
                    if len(t) > 3
                }
            )[:10]
            for word in tokens:
                payload = {"project": project, "query": word, "top_k": 5}
                response = cloud.post("/search", json=payload)
                response.raise_for_status()
                new = response.json()["results"]
                assert new == db.search(project, word, 5)
                response = live.post("/search", json=payload)
                response.raise_for_status()
                old = response.json()["results"]
                queries += 1
                if {r["content"] for r in old} == {r["content"] for r in new}:
                    exact += 1
                else:
                    assert equivalent_cutoff_ties(old, new, db.search(project, word, 1000))
                    tied += 1
        for kind, endpoint, field in (
            ("facts", "/facts", "facts"),
            ("blueprints", "/blueprints", "blueprints"),
        ):
            for project in {r.project for r in records if r.kind == kind}:
                response = cloud.get(
                    endpoint, params={"project": project, "include_superseded": "true"}
                )
                response.raise_for_status()
                assert response.json()[field] == db.list(kind, project)
        digest = hashlib.sha256(
            json.dumps([r.data for r in records], sort_keys=True).encode()
        ).hexdigest()
    print(
        json.dumps(
            {
                "CLOUD_RUN_HEALTH": "PASS",
                "CLOUD_TURSO_PARITY": "PASS",
                "LIVE_ORACLE_QUERIES": queries,
                "EXACT_TOP5": exact,
                "EQUIVALENT_CUTOFF_TIES": tied,
                "SNAPSHOT_PAYLOAD_DIGEST": digest,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("CLOUD_PARITY=FAIL\nERROR_CLASS=" + type(exc).__name__)
        raise SystemExit(1) from None
