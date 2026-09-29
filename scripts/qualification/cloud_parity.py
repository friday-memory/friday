"""Compare a candidate against a privately configured migration source."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.migration.import_to_turso import read_snapshot
from scripts.qualification.compare_backends import equivalent_cutoff_ties
from storage import from_environment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="Private source snapshot directory")
    args = parser.parse_args()

    source_url = os.environ["FRIDAY_SOURCE_URL"]
    source_key = os.environ["FRIDAY_SOURCE_API_KEY"]
    cloud_url = os.environ["FRIDAY_URL"]
    cloud_key = os.environ["FRIDAY_API_KEY"]
    records = read_snapshot(args.source)
    db = from_environment()
    token = subprocess.check_output(
        [os.getenv("FRIDAY_GCLOUD", "gcloud"), "auth", "print-identity-token"],
        text=True,
        stderr=subprocess.DEVNULL,
        timeout=30,
    ).strip()
    cloud_headers = {
        "X-Friday-Key": cloud_key,
        "X-Serverless-Authorization": "Bearer " + token,
    }
    source_headers = {"X-Friday-Key": source_key}

    with (
        httpx.Client(base_url=cloud_url, timeout=60, headers=cloud_headers) as cloud,
        httpx.Client(base_url=source_url, timeout=30, headers=source_headers) as source,
    ):
        with httpx.Client(base_url=cloud_url, timeout=30) as unauthenticated:
            assert unauthenticated.get("/health").status_code in (401, 403)
            assert unauthenticated.get("/facts").status_code in (401, 403)
            assert unauthenticated.get(
                "/facts", headers={"X-Friday-Key": cloud_key}
            ).status_code in (401, 403)
            assert unauthenticated.get(
                "/facts", headers={"X-Serverless-Authorization": "Bearer " + token}
            ).status_code == 401
        assert cloud.get("/health").status_code == source.get("/health").status_code == 200
        for endpoint in (
            "/facts",
            "/search",
            "/state",
            "/api/graph-data",
            "/api/search-quick",
            "/export/persona",
        ):
            assert cloud.get(endpoint).status_code == 200
        memories = [r for r in records if r.kind == "memories"]
        for project in sorted({r.project for r in memories}):
            queries = sorted(
                {
                    word.lower()
                    for record in memories
                    if record.project == project
                    for word in record.data["content"].split()
                    if len(word) > 3
                }
            )[:10]
            for query in queries:
                payload = {"project": project, "query": query, "top_k": 5}
                candidate_response = cloud.post("/search", json=payload)
                candidate_response.raise_for_status()
                candidate = candidate_response.json()["results"]
                assert candidate == db.search(project, query, 5)

                source_response = source.post("/search", json=payload)
                source_response.raise_for_status()
                source_results = source_response.json()["results"]
                assert equivalent_cutoff_ties(
                    source_results, candidate, db.search(project, query, 1000)
                )

        for kind, endpoint, field in (
            ("facts", "/facts", "facts"),
            ("blueprints", "/blueprints", "blueprints"),
        ):
            projects = {r.project for r in records if r.kind == kind}
            for project in projects:
                response = cloud.get(
                    endpoint, params={"project": project, "include_superseded": "true"}
                )
                response.raise_for_status()
                assert response.json()[field] == db.list(kind, project)

    print("SOURCE_CANDIDATE_PARITY=PASS")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("SOURCE_CANDIDATE_PARITY=FAIL\nERROR_CLASS=" + type(exc).__name__)
        raise SystemExit(1) from None
