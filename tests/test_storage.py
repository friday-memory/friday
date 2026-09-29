"""Qualification against independent SQLite and native libSQL engines."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from gateway.serverless import create_app
from storage.local import ConflictError, LocalStorage
from storage.models import Record
from storage.turso import TursoStorage


@pytest.fixture(params=["local", "turso"])
def db(request, tmp_path, monkeypatch):
    monkeypatch.setenv("FRIDAY_STORAGE_BACKEND", request.param)
    path = str(tmp_path / "qualification.db")
    if request.param == "local":
        return LocalStorage(path)
    pytest.importorskip("libsql")
    return TursoStorage(path, initialize=True, allow_local_fixture=True)


def test_records_dedup_isolation_and_reopen(db):
    for project in ("one", "two"):
        first = db.add("facts", project, "same fact")
        assert db.add("facts", project, "same fact")["status"] == "duplicate"
        assert db.list("facts", project)[0]["id"] == first["id"]
    assert db.list("facts", "one")[0]["id"] != db.list("facts", "two")[0]["id"]
    db.add("memories", "one", "deployment running docker")
    db.add("memories", "two", "deployment running turso")
    assert len(db.search("one", 'deployments OR "docker"')) == 1
    assert db.search("none", "deployment") == []
    assert db.search("one", '* : " -') == []
    db.migrate()
    assert len(db.list("facts", "one")) == 1


def test_atomic_import_idempotency_and_conflicts(db):
    records = [
        Record(
            "facts",
            "p",
            "old-id",
            {"id": "old-id", "content": "original", "created_at": "2000-01-01"},
        )
    ]
    assert db.import_records(records) == 1
    assert db.list("facts", "p") == []
    assert db.import_records(records, True) == 1
    assert db.import_records(records, True) == 0
    assert db.import_records(records) == 0
    conflict = [
        Record("facts", "p", "new-id", {"content": "new"}),
        Record("facts", "p", "old-id", {"content": "changed"}),
    ]
    with pytest.raises(ConflictError):
        db.import_records(conflict, True)
    assert db.list("facts", "p") == [records[0].data]
    assert db.add("facts", "p", "original")["id"] == "old-id"


def test_state_blueprints_graph_and_decay(db):
    db.update_state("p", {"urgency_level": 0.8, "response_calibration": {"tone": "calm"}})
    db.update_state("p", {"response_calibration": {"brevity": "high"}})
    assert db.list("states", "p")[0]["response_calibration"]["tone"] == "calm"
    assert db.list("states", "q") == []
    db.ingest("p", "../../never-a-file", "blueprint architecture")
    assert db.list("blueprints", "p")[0]["content"] == "blueprint architecture"
    assert len(db.search("p", "architecture")) == 1
    db.graph_edge("p", "a", "b", "USES")
    db.graph_edge("p", "a", "b", "USES")
    assert len(db.list("entities", "p")) == 2
    assert len(db.list("edges", "p")) == 1
    assert db.list("edges", "q") == []
    date = (datetime.now(timezone.utc) - timedelta(days=28)).isoformat()
    db.import_records(
        [Record("facts", "p", "aged", {"content": "aged", "created_at": date, "energy_score": 1})],
        True,
    )
    db.decay("p")
    first = db.list("facts", "p")[0]["energy_score"]
    db.decay("p")
    assert abs(db.list("facts", "p")[0]["energy_score"] - first) < 0.001
    assert first == pytest.approx(0.25, abs=0.001)


def test_concurrent_dedup(db):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: db.add("facts", "p", "concurrent"), range(8)))
    assert sum(r["status"] == "added" for r in results) == 1


def test_api_auth_and_project_boundaries(db):
    c = TestClient(create_app(db, "qualification-key"))
    paths = [
        "/facts",
        "/search",
        "/state",
        "/api/graph-data",
        "/api/search-quick",
        "/export/persona",
        "/blueprints",
        "/context",
        "/stats",
    ]
    for path in paths:
        for method in ("get", "post"):
            assert getattr(c, method)(path).status_code == 401
        assert c.get(path + "?key=qualification-key").status_code == 401
        assert c.get(path, headers={"X-Friday-Key": "wrong"}).status_code == 401
    assert c.get("/health").status_code == 200
    c.headers["X-Friday-Key"] = "qualification-key"
    assert c.post("/facts", json={"content": "missing project"}).status_code == 422
    assert c.post("/facts", json={"content": "test fact", "project": "p"}).status_code == 200
    assert c.get("/facts?project=q").json()["facts"] == []
    assert c.post("/add", json={"content": "test memory", "project": "p"}).status_code == 200
    assert len(c.post("/search", json={"query": "memory", "project": "p"}).json()["results"]) == 1
    assert c.post("/state/update", json={"project": "p", "urgency_level": 2}).status_code == 422
    assert c.post("/state/update", json={"project": "p", "urgency_level": 0.9}).status_code == 200
    assert c.get("/state?project=p").json()["urgency_level"] == 0.9
    assert (
        c.post("/ingest", json={"project": "p", "filename": "bp", "text": "blueprint"}).status_code
        == 200
    )
    assert c.post("/api/node/create", json={"project": "p", "name": "test"}).status_code == 200
    assert (
        c.post(
            "/api/link/create", json={"project": "p", "source": "test", "target": "other"}
        ).status_code
        == 200
    )
    assert c.get("/api/graph-data?project=q").json() == {"nodes": [], "links": []}
    assert c.post("/dream/run", json={"project": "p"}).status_code == 200


def test_remote_configuration_fails_closed():
    with pytest.raises(ValueError):
        TursoStorage("/tmp/accidental-local.db")
    with pytest.raises(ValueError):
        TursoStorage("libsql://example.turso.io")
    with pytest.raises(RuntimeError):
        create_app(api_key="change_me")


def test_mutations_do_not_cross_projects(db):
    first = db.add("memories", "p", "before")["id"]
    other = db.add("memories", "q", "after")["id"]
    assert db.mutate_memory("q", first, "delete")["status"] == "not_found"
    assert db.mutate_memory("q", first, "update", "changed")["status"] == "not_found"
    assert db.mutate_memory("q", first, "supersede", "after")["status"] == "not_found"
    db.mutate_memory("p", first, "update", "updated")
    assert not db.search("p", "before")
    assert db.search("p", "updated")
    replacement = db.mutate_memory("p", first, "supersede", "after")["new_id"]
    assert replacement != other
    assert db.search("q", "after")[0]["id"] == other
    assert not db.search("p", "updated")
    db.mutate_memory("p", replacement, "delete")
    assert not db.search("p", "after")


def test_snapshot_checksum_and_atomic_failure(tmp_path):
    import hashlib
    import json

    from scripts.migration.import_to_turso import read_snapshot

    data = {kind: [] for kind in ("facts", "memories", "entities", "edges", "blueprints", "states")}
    data["facts"] = [{"id": "source", "content": "private fixture"}]
    raw = json.dumps(data).encode()
    (tmp_path / "snapshot.json").write_bytes(raw)
    manifest = {
        "sha256": {"snapshot.json": hashlib.sha256(raw).hexdigest()},
        "facts_count": 1,
        "memory_count": 0,
        "entity_count": 0,
        "edge_count": 0,
        "blueprint_count": 0,
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    records = read_snapshot(tmp_path)
    assert records[0].project == "__legacy_unscoped__"
    assert records[0].data == data["facts"][0]
    (tmp_path / "snapshot.json").write_bytes(raw + b" ")
    with pytest.raises(ValueError, match="checksum"):
        read_snapshot(tmp_path)


def test_ranking_tie_equivalence_rejects_missing_better_results():
    from scripts.qualification.compare_backends import equivalent_cutoff_ties

    a = {"id": "a", "content": "a", "score": 2.0}
    b = {"id": "b", "content": "b", "score": 1.0}
    c = {"id": "c", "content": "c", "score": 1.0}
    assert equivalent_cutoff_ties([a, b], [a, c], [a, b, c])
    assert not equivalent_cutoff_ties([a, b], [b, c], [a, b, c])
    assert not equivalent_cutoff_ties([a, b], [a, c], [a, c])
