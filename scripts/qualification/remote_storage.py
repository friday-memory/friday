"""Non-production remote qualification using uniquely namespaced fixtures."""

import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi.testclient import TestClient

from gateway.serverless import create_app
from storage import from_environment


def main():
    """Exercise writes and fresh-connection reads only on the dedicated test DB."""
    if "friday-migration-test-" not in os.environ["TURSO_DATABASE_URL"]:
        raise SystemExit("Refusing fixture writes outside friday-migration-test")
    db = from_environment(initialize=True)
    project = "qualification-" + uuid.uuid4().hex
    headers = {"X-Friday-Key": os.environ["FRIDAY_API_KEY"]}
    c = TestClient(create_app(db))
    for path in (
        "/facts",
        "/search",
        "/state",
        "/api/graph-data",
        "/api/search-quick",
        "/export/persona",
    ):
        assert c.get(path).status_code == 401
    c.headers.update(headers)
    payload = {"project": project, "content": "qualification persistent memory"}
    assert c.post("/facts", json=payload).json()["status"] == "added"
    assert c.post("/facts", json=payload).json()["status"] == "duplicate"
    assert c.post("/add", json=payload).json()["status"] == "added"
    assert (
        len(c.post("/search", json={"project": project, "query": "persistent"}).json()["results"])
        == 1
    )
    assert c.get("/facts", params={"project": project + "-other"}).json()["facts"] == []
    assert (
        c.post("/state/update", json={"project": project, "urgency_level": 0.6}).status_code == 200
    )
    assert (
        c.post(
            "/ingest",
            json={"project": project, "filename": "qualification.md", "text": "fixture blueprint"},
        ).status_code
        == 200
    )
    assert c.post("/api/node/create", json={"project": project, "name": "one"}).status_code == 200
    assert (
        c.post(
            "/api/link/create", json={"project": project, "source": "one", "target": "two"}
        ).status_code
        == 200
    )
    assert c.post("/decay/apply", json={"project": project}).status_code == 200
    fresh = from_environment()
    assert len(fresh.list("facts", project)) == 1
    assert len(fresh.list("memories", project)) == 2
    assert len(fresh.list("states", project)) == 1
    assert len(fresh.list("blueprints", project)) == 1
    assert len(fresh.list("entities", project)) == 2
    assert len(fresh.list("edges", project)) == 1
    print(
        "REMOTE_STORAGE=PASS\nFRESH_CONNECTION_PERSISTENCE=PASS\nAUTH_NEGATIVE_TESTS=PASS\nPROJECT_ISOLATION=PASS"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("REMOTE_STORAGE=FAIL\nERROR_CLASS=" + type(exc).__name__)
        raise SystemExit(1) from None
