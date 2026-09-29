"""Tests for Blast Radius Graph Analysis and Smart Fact Conflict Resolution."""

from typing import Any, Dict

import httpx
import pytest
from fastapi.testclient import TestClient

import mcp.server as mcp_server
from friday.client import AsyncFriday, Friday
from friday.types import BlastRadiusResult
from gateway.main import app


def test_sdk_sync_blast_radius():
    """Verify synchronous SDK client retrieves blast radius data correctly."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/graph/blast-radius"
        assert request.url.params.get("entity") == "StripeWebhook"
        assert request.url.params.get("depth") == "2"
        assert request.url.params.get("project") == "reeldm"

        return httpx.Response(
            200,
            json={
                "entity": "StripeWebhook",
                "depth": 2,
                "impacted_nodes": [
                    {"name": "OrdersTable", "distance": 1},
                    {"name": "BillingService", "distance": 2},
                ],
                "relationships": [
                    {"source": "StripeWebhook", "target": "OrdersTable", "type": "UPDATES"},
                    {"source": "OrdersTable", "target": "BillingService", "type": "READS_FROM"},
                ],
                "total_impacted": 2,
                "status": "ok",
            },
        )

    transport = httpx.MockTransport(handler)
    with Friday(api_key="test-key", base_url="http://mock-friday", transport=transport) as client:
        result: BlastRadiusResult = client.get_blast_radius(
            entity="StripeWebhook", depth=2, project="reeldm"
        )
        assert result["entity"] == "StripeWebhook"
        assert result["total_impacted"] == 2
        assert len(result["impacted_nodes"]) == 2
        assert result["impacted_nodes"][0]["name"] == "OrdersTable"


@pytest.mark.anyio
async def test_sdk_async_blast_radius():
    """Verify asynchronous SDK client retrieves blast radius data correctly."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/graph/blast-radius"
        assert request.url.params.get("entity") == "AuthMiddleware"

        return httpx.Response(
            200,
            json={
                "entity": "AuthMiddleware",
                "depth": 1,
                "impacted_nodes": [{"name": "UserSession", "distance": 1}],
                "relationships": [],
                "total_impacted": 1,
                "status": "ok",
            },
        )

    transport = httpx.MockTransport(handler)
    async with AsyncFriday(
        api_key="test-key", base_url="http://mock-friday", transport=transport
    ) as client:
        result = await client.get_blast_radius(entity="AuthMiddleware", depth=1)
        assert result["entity"] == "AuthMiddleware"
        assert result["total_impacted"] == 1
        assert result["status"] == "ok"


def test_sdk_facts_project_and_supersede():
    """Verify SDK fact management carries project scoping and supersede attributes."""
    captured_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/facts":
            data = request.read().decode("utf-8")
            import json

            payload = json.loads(data)
            captured_payloads.append(payload)
            return httpx.Response(200, json={"status": "added", "fact_id": "fact_new"})
        elif request.method == "GET" and request.url.path == "/facts":
            assert request.url.params.get("project") == "reeldm"
            return httpx.Response(
                200,
                json={
                    "total": 1,
                    "facts": [
                        {"id": "fact_new", "content": "Database: PostgreSQL", "project": "reeldm"}
                    ],
                },
            )
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    with Friday(api_key="test-key", base_url="http://mock-friday", transport=transport) as client:
        res = client.add_fact(
            content="Database: PostgreSQL",
            project="reeldm",
            supersedes="fact_old",
            decay_immune=True,
        )
        assert res["status"] == "added"
        assert len(captured_payloads) == 1
        assert captured_payloads[0]["project"] == "reeldm"
        assert captured_payloads[0]["supersedes"] == "fact_old"
        assert captured_payloads[0]["decay_immune"] is True

        facts = client.get_facts(project="reeldm")
        assert len(facts) == 1
        assert facts[0]["content"] == "Database: PostgreSQL"


def test_gateway_fact_auto_supersede(tmp_path, monkeypatch):
    """Verify gateway server-side automatic key conflict resolution and project isolation."""
    facts_file = str(tmp_path / "facts.json")
    monkeypatch.setenv("FACTS_PATH", facts_file)
    monkeypatch.setenv("FRIDAY_API_KEY", "test_key")

    client = TestClient(app)
    headers = {"X-Friday-Key": "test_key"}

    # 1. Add Initial Fact for project 'alpha'
    r1 = client.post(
        "/facts",
        json={"content": "Primary DB: MySQL 8.0", "project": "alpha"},
        headers=headers,
    )
    assert r1.status_code == 200
    fact1_id = r1.json()["fact_id"]

    # 2. Add Conflicting Fact for project 'alpha' (same key: 'Primary DB')
    r2 = client.post(
        "/facts",
        json={"content": "Primary DB: PostgreSQL 16", "project": "alpha"},
        headers=headers,
    )
    assert r2.status_code == 200
    assert "fact_id" in r2.json()
    assert fact1_id in r2.json().get("superseded", [])

    # 3. Add Fact for project 'beta' (isolated)
    r3 = client.post(
        "/facts",
        json={"content": "Primary DB: SQLite", "project": "beta"},
        headers=headers,
    )
    assert r3.status_code == 200

    # 4. Add Global Fact
    r4 = client.post(
        "/facts",
        json={"content": "Company: Acme Corp", "project": "global"},
        headers=headers,
    )
    assert r4.status_code == 200

    # 5. Check active facts for project 'alpha'
    # Should only return PostgreSQL 16 (MySQL superseded) + Global fact
    alpha_facts = client.get("/facts?project=alpha").json()["facts"]
    alpha_contents = [f["content"] for f in alpha_facts]
    assert "Primary DB: PostgreSQL 16" in alpha_contents
    assert "Company: Acme Corp" in alpha_contents
    assert "Primary DB: MySQL 8.0" not in alpha_contents
    assert "Primary DB: SQLite" not in alpha_contents

    # 6. Check include_superseded=true includes superseded entry
    all_alpha_facts = client.get("/facts?project=alpha&include_superseded=true").json()["facts"]
    assert any(
        f["content"] == "Primary DB: MySQL 8.0" and f.get("superseded") for f in all_alpha_facts
    )

    # 7. Check export_persona filters by project
    persona_res = client.get("/export/persona?project=alpha", headers=headers)
    assert persona_res.status_code == 200
    assert "Primary DB: PostgreSQL 16" in persona_res.text
    assert "Primary DB: SQLite" not in persona_res.text


def test_gateway_blast_radius_offline_fallback():
    """Verify gateway blast radius endpoint returns graceful fallback when Neo4j is offline."""
    client = TestClient(app)
    headers = {"X-Friday-Key": "test_key"}
    r = client.get("/graph/blast-radius?entity=AuthModule&depth=2", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["entity"] == "AuthModule"
    assert data["total_impacted"] == 0
    assert data["status"] in ["neo4j_unavailable", "ok"]


@pytest.mark.anyio
async def test_mcp_tools_blast_radius_and_facts(monkeypatch):
    """Verify MCP server handlers forward arguments correctly to gateway endpoints."""
    called_urls: Dict[str, Any] = {}

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def get(self, url, headers=None, params=None):
            called_urls["get_url"] = url
            called_urls["get_params"] = params

            class MockResponse:
                is_success = True
                status_code = 200

                def json(self):
                    if "blast-radius" in url:
                        return {"entity": params.get("entity"), "total_impacted": 3}
                    return {"facts": [{"content": "Mock Fact"}]}

                def raise_for_status(self):
                    pass

            return MockResponse()

        async def post(self, url, headers=None, json=None):
            called_urls["post_url"] = url
            called_urls["post_json"] = json

            class MockResponse:
                is_success = True
                status_code = 200

                def json(self):
                    return {"status": "added", "fact_id": "mcp_fact_1"}

                def raise_for_status(self):
                    pass

            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    # Test MCP add_fact handler
    fact_res = await mcp_server.add_fact(
        {
            "content": "Framework: FastAPI",
            "project": "reeldm",
            "supersedes": "old_fact_99",
        }
    )
    assert fact_res["status"] == "added"
    assert called_urls["post_json"]["project"] == "reeldm"
    assert called_urls["post_json"]["supersedes"] == "old_fact_99"

    # Test MCP get_blast_radius handler
    blast_res = await mcp_server.get_blast_radius(
        {
            "entity": "PaymentService",
            "depth": 3,
            "project": "reeldm",
        }
    )
    assert blast_res["total_impacted"] == 3
    assert called_urls["get_params"]["entity"] == "PaymentService"
    assert called_urls["get_params"]["depth"] == 3
    assert called_urls["get_params"]["project"] == "reeldm"

    # Test MCP get_context handler with project
    ctx_res = await mcp_server.get_context({"project": "reeldm"})
    assert "facts" in ctx_res
    assert called_urls["get_params"]["project"] == "reeldm"
