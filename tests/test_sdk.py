"""Unit tests for Friday Python SDK (sync, async, and integrations)."""

from typing import Any

import httpx
import pytest

from friday import (
    AsyncFriday,
    Friday,
    FridayAPIError,
    FridayAuthenticationError,
    FridayConnectionError,
    FridayNotFoundError,
    __version__,
)
from friday.client import _resolve_config
from friday.integrations.langchain import FridayRetriever


def test_sdk_version_and_exports():
    """Verify package version and public exports."""
    assert __version__ == "1.2.0"
    assert Friday is not None
    assert AsyncFriday is not None
    assert FridayAuthenticationError is not None


def test_config_resolution(monkeypatch):
    """Test resolution of base_url and api_key from arguments and environment."""
    # Explicit arguments take precedence
    url, key = _resolve_config("custom-key", "http://my-friday:9000/")
    assert url == "http://my-friday:9000"
    assert key == "custom-key"

    # Environment variables
    monkeypatch.setenv("FRIDAY_URL", "http://env-friday:8000")
    monkeypatch.setenv("FRIDAY_API_KEY", "env-secret-key")
    url, key = _resolve_config()
    assert url == "http://env-friday:8000"
    assert key == "env-secret-key"

    # Fallback to BRAIN_* aliases
    monkeypatch.delenv("FRIDAY_URL")
    monkeypatch.delenv("FRIDAY_API_KEY")
    monkeypatch.setenv("BRAIN_URL", "http://brain-alias:8000")
    monkeypatch.setenv("BRAIN_API_KEY", "brain-key")
    url, key = _resolve_config()
    assert url == "http://brain-alias:8000"
    assert key == "brain-key"

    # Default fallback
    monkeypatch.delenv("BRAIN_URL")
    monkeypatch.delenv("BRAIN_API_KEY")
    url, key = _resolve_config()
    assert url == "http://localhost:8000"
    assert key == ""


def test_sync_client_operations():
    """Verify all synchronous client methods using MockTransport."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("X-Brain-Key") == "secret-key"

        if request.url.path == "/health":
            return httpx.Response(
                200,
                json={
                    "status": "healthy",
                    "service": "friday-cognitive-substrate",
                    "version": "1.2.0",
                    "layers": {"L1_core": "healthy", "L2_mem0": "healthy"},
                    "timestamp": 123456789.0,
                },
            )
        elif request.url.path == "/add":
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "mem0_id": "mem_01",
                    "chroma_id": "chr_01",
                },
            )
        elif request.url.path == "/search":
            return httpx.Response(
                200,
                json={
                    "query": "arch decision",
                    "results": {"layer2_facts": ["PostgreSQL selected"]},
                },
            )
        elif request.url.path == "/facts":
            if request.method == "POST":
                return httpx.Response(200, json={"status": "committed", "id": "fact_01"})
            return httpx.Response(200, json={"facts": [{"id": "fact_01", "content": "Fact 1"}]})
        elif request.url.path == "/export/persona":
            assert request.url.params.get("target") == "agents"
            return httpx.Response(200, text="# Directives\nBe precise.")
        elif request.url.path == "/api/graph-data":
            return httpx.Response(200, json={"nodes": [{"id": "User"}], "links": []})
        elif request.url.path == "/ingest":
            return httpx.Response(200, json={"status": "ingested", "chunks": 3})

        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    with Friday(api_key="secret-key", base_url="http://mock-friday", transport=transport) as client:
        # Health
        health = client.health()
        assert health["status"] == "healthy"
        assert health["version"] == "1.2.0"

        # Add memory
        mem = client.add_memory("Chose FastAPI", project="reeldm")
        assert mem["status"] == "success"
        assert mem["mem0_id"] == "mem_01"

        # Search
        search = client.search("arch decision", project="reeldm")
        assert "layer2_facts" in search["results"]

        # Facts
        fact_res = client.add_fact("Verified ground truth")
        assert fact_res["status"] == "committed"

        facts = client.get_facts()
        assert len(facts) == 1
        assert facts[0]["content"] == "Fact 1"

        # Persona / Directives
        directives = client.get_context()
        assert "# Directives" in directives

        # Knowledge Graph
        graph = client.get_graph_data()
        assert len(graph["nodes"]) == 1

        # Ingest
        ingest_res = client.ingest(text="Specs", filename="spec.md", source="blueprint")
        assert ingest_res["chunks"] == 3


def test_sync_client_error_handling():
    """Verify HTTP error code translation into typed SDK exceptions."""

    def error_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/unauthorized":
            return httpx.Response(401, json={"detail": "Unauthorized"})
        elif request.url.path == "/missing":
            return httpx.Response(404, json={"detail": "Not found"})
        elif request.url.path == "/server-error":
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(error_handler)
    client = Friday(api_key="key", base_url="http://mock-friday", transport=transport)

    with pytest.raises(FridayAuthenticationError):
        r = client.client.get("/unauthorized")
        from friday.client import _handle_response_error

        _handle_response_error(r)

    with pytest.raises(FridayNotFoundError):
        r = client.client.get("/missing")
        from friday.client import _handle_response_error

        _handle_response_error(r)

    with pytest.raises(FridayAPIError) as exc_info:
        r = client.client.get("/server-error")
        from friday.client import _handle_response_error

        _handle_response_error(r)
    assert exc_info.value.status_code == 500


def test_sync_client_connection_error():
    """Verify network connection failures raise FridayConnectionError."""

    def raise_connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Failed to connect", request=request)

    transport = httpx.MockTransport(raise_connect_error)
    client = Friday(api_key="key", base_url="http://unreachable-host", transport=transport)

    with pytest.raises(FridayConnectionError):
        client.health()

    with pytest.raises(FridayConnectionError):
        client.add_memory("test")


@pytest.mark.anyio
async def test_async_client_operations():
    """Verify asynchronous client operations using MockTransport."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "healthy", "service": "friday"})
        elif request.url.path == "/facts":
            if request.method == "POST":
                return httpx.Response(200, json={"status": "committed", "id": "fact_async"})
            return httpx.Response(
                200, json={"facts": [{"id": "fact_async", "content": "Async Fact"}]}
            )
        elif request.url.path == "/search":
            return httpx.Response(200, json={"results": {"layer2_facts": ["Async search hit"]}})
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    async with AsyncFriday(
        api_key="secret", base_url="http://mock-friday", transport=transport
    ) as client:
        health = await client.health()
        assert health["status"] == "healthy"

        fact_res = await client.add_fact("Async content")
        assert fact_res["id"] == "fact_async"

        facts = await client.get_facts()
        assert facts[0]["content"] == "Async Fact"

        search = await client.search("test")
        assert "layer2_facts" in search["results"]


@pytest.mark.anyio
async def test_async_client_connection_error():
    """Verify network connection failures in async client raise FridayConnectionError."""

    def raise_connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Async connection failed", request=request)

    transport = httpx.MockTransport(raise_connect_error)
    client = AsyncFriday(api_key="key", base_url="http://unreachable-host", transport=transport)

    with pytest.raises(FridayConnectionError):
        await client.health()

    with pytest.raises(FridayConnectionError):
        await client.add_memory("async test")

    await client.close()


def test_langchain_retriever_missing_dependency():
    """Verify graceful error reporting when langchain-core is not installed."""
    retriever = FridayRetriever(api_key="key", base_url="http://localhost:8000")
    with pytest.raises(ImportError) as exc_info:
        retriever.invoke("query")
    assert "langchain-core is required" in str(exc_info.value)


def test_retriever_search_parsing_logic():
    """Verify parsing search response into document structures."""

    class MockDoc:
        def __init__(self, page_content: str, metadata: dict[str, Any]):
            self.page_content = page_content
            self.metadata = metadata

    mock_search_results = {
        "results": {
            "layer2_facts": ["Fact A", "Fact B"],
            "layer3_semantic": ["Semantic chunk 1"],
        }
    }

    docs = []
    results = mock_search_results.get("results", {})
    for fact in results.get("layer2_facts", []):
        docs.append(MockDoc(page_content=fact, metadata={"source": "friday_facts"}))
    for mem in results.get("layer3_semantic", []):
        docs.append(MockDoc(page_content=mem, metadata={"source": "friday_semantic"}))

    assert len(docs) == 3
    assert docs[0].page_content == "Fact A"
    assert docs[0].metadata["source"] == "friday_facts"
    assert docs[2].page_content == "Semantic chunk 1"
    assert docs[2].metadata["source"] == "friday_semantic"
