"""Capture/verify candidate API fixture hashes across a process replacement."""

import argparse
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

import httpx


def main():
    """Only write qualification namespaces to the dedicated test database."""
    p = argparse.ArgumentParser()
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--verify", action="store_true")
    args = p.parse_args()
    if "friday-migration-test-" not in os.environ["TURSO_DATABASE_URL"]:
        raise SystemExit("Requires qualification database")
    os.umask(0o077)
    headers = {"X-Friday-Key": os.environ["FRIDAY_API_KEY"]}
    paths = ["/facts", "/state", "/blueprints", "/api/graph-data", "/context"]
    with httpx.Client(base_url=os.environ["FRIDAY_URL"], timeout=30) as c:
        for attempt in range(30):
            try:
                if c.get("/health").status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Candidate readiness timeout")
        for endpoint in (
            "/facts",
            "/search",
            "/state",
            "/api/graph-data",
            "/api/search-quick",
            "/export/persona",
        ):
            assert c.get(endpoint).status_code in (401, 403)
            assert c.post(endpoint, json={}).status_code in (401, 403)
        c.headers.update(headers)
        if args.verify:
            evidence = json.loads(args.evidence.read_text())
            project = evidence["project"]
        else:
            project = "qualification-http-" + uuid.uuid4().hex
            evidence = {"project": project, "hashes": {}}
            operations = [
                ("/facts", {"content": "qualification fact"}),
                ("/add", {"content": "qualification memory"}),
                ("/state/update", {"urgency_level": 0.4}),
                ("/ingest", {"filename": "qualification.md", "text": "qualification blueprint"}),
                ("/api/node/create", {"name": "a"}),
                ("/api/link/create", {"source": "a", "target": "b"}),
            ]
            for path, payload in operations:
                r = c.post(path, json=dict(payload, project=project))
                r.raise_for_status()
            r = c.post("/search", json={"project": project, "query": "qualification"})
            r.raise_for_status()
            assert len(r.json()["results"]) == 2
        for path in paths:
            r = c.get(path, params={"project": project})
            r.raise_for_status()
            digest = hashlib.sha256(json.dumps(r.json(), sort_keys=True).encode()).hexdigest()
            if args.verify:
                assert evidence["hashes"][path] == digest
            else:
                evidence["hashes"][path] = digest
        if not args.verify:
            with args.evidence.open("x") as f:
                json.dump(evidence, f)
    print("AUTH_NEGATIVE_TESTS=PASS\nCANDIDATE_HTTP=PASS")
    print("RESTART_PERSISTENCE=PASS" if args.verify else "PERSISTENCE_BASELINE=CAPTURED")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("CANDIDATE_HTTP=FAIL\nERROR_CLASS=" + type(exc).__name__)
        raise SystemExit(1) from None
