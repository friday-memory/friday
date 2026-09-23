"""Friday Python SDK — Core Client Implementation.

Provides synchronous (`Friday`) and asynchronous (`AsyncFriday`) clients
for interacting with the self-hosted Friday cognitive memory substrate.
"""

import os
from typing import Any, Dict, List, Optional

import httpx

from .exceptions import (
    FridayAPIError,
    FridayAuthenticationError,
    FridayConnectionError,
    FridayNotFoundError,
)
from .types import Fact, GraphData, HealthStatus, MemoryResult


def _resolve_config(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> tuple[str, str]:
    resolved_url = (
        base_url
        or os.environ.get("FRIDAY_URL")
        or os.environ.get("BRAIN_URL")
        or "http://localhost:8000"
    ).rstrip("/")
    resolved_key = (
        api_key or os.environ.get("FRIDAY_API_KEY") or os.environ.get("BRAIN_API_KEY") or ""
    )
    return resolved_url, resolved_key


def _handle_response_error(response: httpx.Response) -> None:
    if response.is_success:
        return

    if response.status_code == 401:
        raise FridayAuthenticationError("Invalid or missing API key.")
    elif response.status_code == 404:
        raise FridayNotFoundError(f"Resource not found: {response.url}")
    else:
        raise FridayAPIError(
            message=f"HTTP {response.status_code}",
            status_code=response.status_code,
            response_text=response.text,
        )


class Friday:
    """Synchronous Friday Cognitive Memory Client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self.base_url, self.api_key = _resolve_config(api_key, base_url)
        self.headers = {
            "Content-Type": "application/json",
            "X-Brain-Key": self.api_key,
        }
        self.client = httpx.Client(
            base_url=self.base_url,
            headers=self.headers,
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> "Friday":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self.client.close()

    def health(self) -> HealthStatus:
        """Check the health status of all Friday memory layers."""
        try:
            r = self.client.get("/health")
            _handle_response_error(r)
            return r.json()
        except httpx.ConnectError as e:
            raise FridayConnectionError(
                f"Could not connect to Friday at {self.base_url}: {e}"
            ) from e
        except httpx.TimeoutException as e:
            raise FridayConnectionError(
                f"Connection timed out connecting to Friday at {self.base_url}: {e}"
            ) from e

    def add_memory(self, content: str, project: str = "default") -> MemoryResult:
        """Store an architectural decision or context chunk into episodic memory."""
        try:
            payload = {"content": content, "project": project}
            r = self.client.post("/add", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error adding memory: {e}") from e

    def search(self, query: str, project: Optional[str] = None) -> Dict[str, Any]:
        """Search memory layers semantically for relevant architectural context."""
        try:
            payload: Dict[str, Any] = {"query": query}
            if project:
                payload["project"] = project
            r = self.client.post("/search", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error searching memory: {e}") from e

    def add_fact(self, content: str) -> Dict[str, Any]:
        """Commit an atomic, versioned ground-truth fact to the facts ledger."""
        try:
            payload = {"content": content}
            r = self.client.post("/facts", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error adding fact: {e}") from e

    def get_facts(self, include_superseded: bool = False) -> List[Fact]:
        """Retrieve verified ground-truth facts from the ledger."""
        try:
            url = "/facts?include_superseded=true" if include_superseded else "/facts"
            r = self.client.get(url)
            _handle_response_error(r)
            data = r.json()
            return data.get("facts", [])
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error retrieving facts: {e}") from e

    def get_context(self, query: Optional[str] = None, target: str = "agents") -> str:
        """Export compiled architectural directives and verified facts for prompt injection."""
        try:
            url = f"/export/persona?target={target}"
            r = self.client.get(url)
            _handle_response_error(r)
            return r.text
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error retrieving context: {e}") from e

    def get_graph_data(self) -> GraphData:
        """Fetch all entities and typed relationships from the Neo4j knowledge graph."""
        try:
            r = self.client.get("/api/graph-data")
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error retrieving graph data: {e}") from e

    def ingest(
        self, text: str, filename: Optional[str] = None, source: str = "document"
    ) -> Dict[str, Any]:
        """Batch ingest architectural specifications or documentation into the knowledge base."""
        try:
            payload = {"text": text, "source": source}
            if filename:
                payload["filename"] = filename
            r = self.client.post("/ingest", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error ingesting document: {e}") from e


class AsyncFriday:
    """Asynchronous Friday Cognitive Memory Client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.base_url, self.api_key = _resolve_config(api_key, base_url)
        self.headers = {
            "Content-Type": "application/json",
            "X-Brain-Key": self.api_key,
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=timeout,
            transport=transport,
        )

    async def __aenter__(self) -> "AsyncFriday":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()

    async def health(self) -> HealthStatus:
        """Check the health status of all Friday memory layers."""
        try:
            r = await self.client.get("/health")
            _handle_response_error(r)
            return r.json()
        except httpx.ConnectError as e:
            raise FridayConnectionError(
                f"Could not connect to Friday at {self.base_url}: {e}"
            ) from e
        except httpx.TimeoutException as e:
            raise FridayConnectionError(
                f"Connection timed out connecting to Friday at {self.base_url}: {e}"
            ) from e

    async def add_memory(self, content: str, project: str = "default") -> MemoryResult:
        """Store an architectural decision or context chunk into episodic memory."""
        try:
            payload = {"content": content, "project": project}
            r = await self.client.post("/add", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error adding memory: {e}") from e

    async def search(self, query: str, project: Optional[str] = None) -> Dict[str, Any]:
        """Search memory layers semantically for relevant architectural context."""
        try:
            payload: Dict[str, Any] = {"query": query}
            if project:
                payload["project"] = project
            r = await self.client.post("/search", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error searching memory: {e}") from e

    async def add_fact(self, content: str) -> Dict[str, Any]:
        """Commit an atomic, versioned ground-truth fact to the facts ledger."""
        try:
            payload = {"content": content}
            r = await self.client.post("/facts", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error adding fact: {e}") from e

    async def get_facts(self, include_superseded: bool = False) -> List[Fact]:
        """Retrieve verified ground-truth facts from the ledger."""
        try:
            url = "/facts?include_superseded=true" if include_superseded else "/facts"
            r = await self.client.get(url)
            _handle_response_error(r)
            data = r.json()
            return data.get("facts", [])
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error retrieving facts: {e}") from e

    async def get_context(self, query: Optional[str] = None, target: str = "agents") -> str:
        """Export compiled architectural directives and verified facts for prompt injection."""
        try:
            url = f"/export/persona?target={target}"
            r = await self.client.get(url)
            _handle_response_error(r)
            return r.text
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error retrieving context: {e}") from e

    async def get_graph_data(self) -> GraphData:
        """Fetch all entities and typed relationships from the Neo4j knowledge graph."""
        try:
            r = await self.client.get("/api/graph-data")
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error retrieving graph data: {e}") from e

    async def ingest(
        self, text: str, filename: Optional[str] = None, source: str = "document"
    ) -> Dict[str, Any]:
        """Batch ingest architectural specifications or documentation into the knowledge base."""
        try:
            payload = {"text": text, "source": source}
            if filename:
                payload["filename"] = filename
            r = await self.client.post("/ingest", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error ingesting document: {e}") from e
