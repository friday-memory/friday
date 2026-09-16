"""
Friday — Smoke Tests

Tests core Friday API without external services (Neo4j, Mem0).
Uses FastAPI TestClient with mocked dependencies.
"""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Use a writable temp path for facts in local testing
_TMP_FACTS = os.path.join(tempfile.gettempdir(), "friday_test_facts.json")
os.environ.setdefault("BRAIN_API_KEY", "test_key")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "test_password")
os.environ["FACTS_PATH"] = _TMP_FACTS  # Override to writable temp dir

from gateway.main import app

client = TestClient(app)
HEADERS = {"X-Brain-Key": "test_key"}


def test_studio_loads():
    """Neural Studio page should return 200."""
    r = client.get("/")
    assert r.status_code == 200


def test_health_endpoint():
    """Health check should always respond."""
    with patch("gateway.main.get_neo4j_driver", return_value=None), \
         patch("gateway.main.get_mem0_client", return_value=None):
        r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "layers" in data


def test_facts_get_public():
    """Facts endpoint is public — no auth needed."""
    r = client.get("/facts")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "facts" in data


def test_facts_add_requires_auth():
    """Adding facts requires the Brain API key."""
    r = client.post("/facts", json={"content": "Test fact"})
    assert r.status_code == 401


def test_facts_add_with_auth():
    """Adding a fact with correct key should succeed."""
    r = client.post("/facts", json={"content": "Test fact from pytest"}, headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("added", "duplicate")


def test_add_memory_requires_auth():
    """Memory add endpoint requires auth."""
    r = client.post("/add", json={"content": "test memory"})
    assert r.status_code == 401


def test_search_requires_auth():
    """Search endpoint requires auth."""
    r = client.post("/search", json={"query": "test"})
    assert r.status_code == 401


def test_graph_data_public():
    """Graph data endpoint is public."""
    with patch("gateway.main.get_neo4j_driver", return_value=None):
        r = client.get("/api/graph-data")
    assert r.status_code == 200
    data = r.json()
    assert "nodes" in data
    assert "links" in data


def test_quick_search_public():
    """Quick search is public."""
    with patch("gateway.main.get_neo4j_driver", return_value=None):
        r = client.get("/api/search-quick?q=test")
    assert r.status_code == 200


def teardown_module(module):
    """Cleanup temp facts file after tests."""
    if os.path.exists(_TMP_FACTS):
        os.remove(_TMP_FACTS)
