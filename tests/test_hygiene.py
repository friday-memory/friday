"""Tests for Memory and Fact Hygiene Parity (delete_memory, update_memory, revoke_fact, delete_fact)."""

from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

import mcp.server as mcp_server
from friday.client import AsyncFriday, Friday
from gateway.main import app
from gateway.serverless import create_app
from storage.local import LocalStorage

# ── 1. Gateway Main: Facts Revocation & Deletion ───────────────────────────────

def test_gateway_fact_revoke_requires_auth():
    """Revoking a fact requires Brain API key."""
    client = TestClient(app)
    r = client.post("/facts/revoke", json={"fact_id": "nonexistent"})
    assert r.status_code == 401


def test_gateway_fact_delete_requires_auth():
    """Deleting a fact requires Brain API key."""
    client = TestClient(app)
    r = client.delete("/facts/fact_123")
    assert r.status_code == 401


def test_gateway_fact_revoke_and_filter(tmp_path, monkeypatch):
    """Test full fact revocation lifecycle and automatic exclusion from active views."""
    facts_file = str(tmp_path / "facts.json")
    monkeypatch.setenv("FACTS_PATH", facts_file)
    monkeypatch.setenv("FRIDAY_API_KEY", "test_key")

    client = TestClient(app)
    headers = {"X-Friday-Key": "test_key"}

    # 1. Add Fact
    r1 = client.post(
        "/facts",
        json={"content": "Infra: AWS ap-south-2", "project": "infra"},
        headers=headers,
    )
    assert r1.status_code == 200
    fact_id = r1.json()["fact_id"]

    # Verify present in active facts
    facts = client.get("/facts?project=infra").json()["facts"]
    assert any(f["id"] == fact_id for f in facts)

    # 2. Revoke Fact
    r_revoke = client.post(
        "/facts/revoke",
        json={"fact_id": fact_id, "reason": "Migrated to hybrid cloud", "project": "infra"},
        headers=headers,
    )
    assert r_revoke.status_code == 200
    data = r_revoke.json()
    assert data["status"] == "revoked"
    assert data["fact_id"] == fact_id
    assert data["reason"] == "Migrated to hybrid cloud"

    # 3. Verify excluded from active /facts
    active_facts = client.get("/facts?project=infra").json()["facts"]
    assert not any(f["id"] == fact_id for f in active_facts)

    # 4. Verify present when include_superseded=True
    all_facts = client.get("/facts?project=infra&include_superseded=true").json()["facts"]
    revoked_entry = next((f for f in all_facts if f["id"] == fact_id), None)
    assert revoked_entry is not None
    assert revoked_entry["status"] == "revoked"
    assert revoked_entry["superseded"] is True

    # 5. Verify excluded from persona export
    persona = client.get("/export/persona?project=infra", headers=headers).text
    assert "Infra: AWS ap-south-2" not in persona

    # 6. Revoking non-existent fact yields 404
    r_404 = client.post(
        "/facts/revoke",
        json={"fact_id": "nonexistent_id"},
        headers=headers,
    )
    assert r_404.status_code == 404


def test_gateway_fact_delete_soft_and_hard(tmp_path, monkeypatch):
    """Test soft-delete (revoke) vs hard-delete on facts."""
    facts_file = str(tmp_path / "facts.json")
    monkeypatch.setenv("FACTS_PATH", facts_file)
    monkeypatch.setenv("FRIDAY_API_KEY", "test_key")

    client = TestClient(app)
    headers = {"X-Friday-Key": "test_key"}

    # Add 2 facts
    f1 = client.post("/facts", json={"content": "Soft Fact"}, headers=headers).json()["fact_id"]
    f2 = client.post("/facts", json={"content": "Hard Fact"}, headers=headers).json()["fact_id"]

    # Soft delete f1 (default hard=False)
    r_soft = client.delete(f"/facts/{f1}", headers=headers)
    assert r_soft.status_code == 200
    assert r_soft.json()["status"] == "revoked"
    assert r_soft.json()["hard"] is False

    # Hard delete f2 (hard=True)
    r_hard = client.delete(f"/facts/{f2}?hard=true", headers=headers)
    assert r_hard.status_code == 200
    assert r_hard.json()["status"] == "deleted"
    assert r_hard.json()["hard"] is True

    # f1 should be in all_facts as revoked, f2 should be completely gone
    all_facts = client.get("/facts?include_superseded=true").json()["facts"]
    assert any(f["id"] == f1 and f["status"] == "revoked" for f in all_facts)
    assert not any(f["id"] == f2 for f in all_facts)


# ── 2. Gateway Main: Memory Deletion & Update ───────────────────────────────────

def test_gateway_memory_delete_and_update_requires_auth():
    """Memory delete and update endpoints require auth."""
    client = TestClient(app)
    assert client.post("/delete", json={"memory_id": "mem_1"}).status_code == 401
    assert client.delete("/memory/mem_1").status_code == 401
    assert client.post("/update", json={"memory_id": "mem_1", "content": "Updated"}).status_code == 401


def test_gateway_memory_delete_and_update_with_auth():
    """Test memory delete and update endpoints with mock Mem0 client."""
    client = TestClient(app)
    headers = {"X-Friday-Key": "test_key"}

    deleted_ids = []
    updated_calls = []

    class MockMem0:
        def delete(self, mid):
            deleted_ids.append(mid)

        def update(self, mid, data=None):
            updated_calls.append((mid, data))

    with patch("gateway.main.get_mem0_client", return_value=MockMem0()):
        # POST /delete
        r_del = client.post("/delete", json={"memory_id": "mem_99", "project": "reeldm"}, headers=headers)
        assert r_del.status_code == 200
        assert r_del.json()["status"] == "deleted"
        assert "mem_99" in deleted_ids

        # DELETE /memory/{id}
        r_del_id = client.delete("/memory/mem_100", headers=headers)
        assert r_del_id.status_code == 200
        assert "mem_100" in deleted_ids

        # POST /update
        r_up = client.post(
            "/update",
            json={"memory_id": "mem_99", "content": "Updated architectural choice", "project": "reeldm"},
            headers=headers,
        )
        assert r_up.status_code == 200
        assert r_up.json()["status"] == "updated"
        assert updated_calls == [("mem_99", "Updated architectural choice")]


# ── 3. Serverless Candidate Hygiene Parity ─────────────────────────────────────

def test_serverless_fact_revoke_and_delete(tmp_path):
    """Verify Serverless candidate gateway supports /facts/revoke and DELETE /facts/{id}."""
    store = LocalStorage(str(tmp_path / "serverless.db"))
    store.migrate()

    app_serverless = create_app(store=store, api_key="secret-key")
    client = TestClient(app_serverless)
    headers = {"X-Friday-Key": "secret-key"}

    # Add a fact
    r_add = client.post("/facts", json={"content": "Serverless Truth", "project": "cloud"}, headers=headers)
    assert r_add.status_code == 200
    fact_id = r_add.json()["fact_id"]

    # Revoke fact
    r_revoke = client.post(
        "/facts/revoke",
        json={"fact_id": fact_id, "project": "cloud", "reason": "Outdated"},
        headers=headers,
    )
    assert r_revoke.status_code == 200
    assert r_revoke.json()["status"] == "revoked"

    # Verify excluded from active list
    facts = client.get("/facts?project=cloud", headers=headers).json()["facts"]
    assert not any(f["id"] == fact_id for f in facts)

    # Delete fact hard
    r_add2 = client.post("/facts", json={"content": "Another Fact", "project": "cloud"}, headers=headers)
    f2_id = r_add2.json()["fact_id"]
    r_del = client.delete(f"/facts/{f2_id}?project=cloud&hard=true", headers=headers)
    assert r_del.status_code == 200
    assert r_del.json()["status"] == "deleted"


# ── 4. MCP Tools: delete_memory and revoke_fact ────────────────────────────────

@pytest.mark.anyio
async def test_mcp_delete_memory_and_revoke_fact(monkeypatch):
    """Verify MCP tools forward delete_memory and revoke_fact calls to Friday server."""
    called_requests = []

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def post(self, url, headers=None, json=None):
            called_requests.append({"method": "POST", "url": url, "json": json})

            class MockResponse:
                is_success = True
                status_code = 200

                def json(self):
                    if "/delete" in url:
                        return {"status": "deleted", "memory_id": json.get("memory_id")}
                    elif "/facts/revoke" in url:
                        return {"status": "revoked", "fact_id": json.get("fact_id")}
                    return {"status": "ok"}

                def raise_for_status(self):
                    pass

            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    # 1. MCP delete_memory
    del_res = await mcp_server.delete_memory({"memory_id": "mem_alpha", "project": "reeldm"})
    assert del_res["status"] == "deleted"
    assert del_res["memory_id"] == "mem_alpha"
    assert any(r["url"].endswith("/delete") and r["json"]["memory_id"] == "mem_alpha" for r in called_requests)

    # 2. MCP revoke_fact
    rev_res = await mcp_server.revoke_fact({
        "fact_id": "fact_beta",
        "reason": "Deprecated in v2",
        "project": "reeldm",
    })
    assert rev_res["status"] == "revoked"
    assert rev_res["fact_id"] == "fact_beta"
    assert any(r["url"].endswith("/facts/revoke") and r["json"]["fact_id"] == "fact_beta" for r in called_requests)


# ── 5. Python SDK: Friday & AsyncFriday Client Methods ─────────────────────────

def test_sdk_sync_hygiene_methods():
    """Verify Friday SDK client provides delete_memory, update_memory, revoke_fact, and delete_fact."""
    called_routes = []

    def handler(request: httpx.Request) -> httpx.Response:
        called_routes.append({"method": request.method, "path": request.url.path})

        if request.url.path == "/delete" and request.method == "POST":
            return httpx.Response(200, json={"status": "deleted", "id": "mem_1"})
        elif request.url.path == "/update" and request.method == "POST":
            return httpx.Response(200, json={"status": "updated", "id": "mem_1"})
        elif request.url.path == "/facts/revoke" and request.method == "POST":
            return httpx.Response(200, json={"status": "revoked", "fact_id": "fact_1"})
        elif request.url.path == "/facts/fact_1" and request.method == "DELETE":
            return httpx.Response(200, json={"status": "deleted", "fact_id": "fact_1"})
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    with Friday(api_key="key", base_url="http://mock-friday", transport=transport) as client:
        # delete_memory
        r1 = client.delete_memory("mem_1", project="test")
        assert r1["status"] == "deleted"

        # update_memory
        r2 = client.update_memory("mem_1", content="New content", project="test")
        assert r2["status"] == "updated"

        # revoke_fact
        r3 = client.revoke_fact("fact_1", reason="Obsolete", project="test")
        assert r3["status"] == "revoked"

        # delete_fact
        r4 = client.delete_fact("fact_1", hard=True)
        assert r4["status"] == "deleted"

    assert len(called_routes) == 4


@pytest.mark.anyio
async def test_sdk_async_hygiene_methods():
    """Verify AsyncFriday client provides delete_memory, update_memory, revoke_fact, and delete_fact."""
    called_routes = []

    def handler(request: httpx.Request) -> httpx.Response:
        called_routes.append({"method": request.method, "path": request.url.path})

        if request.url.path == "/delete" and request.method == "POST":
            return httpx.Response(200, json={"status": "deleted", "id": "mem_async_1"})
        elif request.url.path == "/update" and request.method == "POST":
            return httpx.Response(200, json={"status": "updated", "id": "mem_async_1"})
        elif request.url.path == "/facts/revoke" and request.method == "POST":
            return httpx.Response(200, json={"status": "revoked", "fact_id": "fact_async_1"})
        elif request.url.path == "/facts/fact_async_1" and request.method == "DELETE":
            return httpx.Response(200, json={"status": "deleted", "fact_id": "fact_async_1"})
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    async with AsyncFriday(api_key="key", base_url="http://mock-friday", transport=transport) as client:
        # delete_memory
        r1 = await client.delete_memory("mem_async_1", project="test")
        assert r1["status"] == "deleted"

        # update_memory
        r2 = await client.update_memory("mem_async_1", content="New content", project="test")
        assert r2["status"] == "updated"

        # revoke_fact
        r3 = await client.revoke_fact("fact_async_1", reason="Obsolete", project="test")
        assert r3["status"] == "revoked"

        # delete_fact
        r4 = await client.delete_fact("fact_async_1", hard=False)
        assert r4["status"] == "deleted"

    assert len(called_routes) == 4
