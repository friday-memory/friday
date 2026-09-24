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
from .types import (
    CognitiveState,
    DreamReport,
    Fact,
    GraphData,
    HealthStatus,
    MemoryDecayReport,
    MemoryResult,
)


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
        """Close underlying HTTP client connection pool."""
        self.client.close()

    def health(self) -> HealthStatus:
        """Query cognitive substrate health status and layer connectivity."""
        try:
            r = self.client.get("/health")
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(
                f"Cannot connect to Friday server at {self.base_url}: {e}"
            ) from e

    def add_memory(self, content: str, project: str = "default") -> MemoryResult:
        """Store conversational or episodic memory, triggering autonomous graph extraction."""
        try:
            r = self.client.post("/add", json={"content": content, "project": project})
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error storing memory: {e}") from e

    def search(self, query: str, project: Optional[str] = None) -> Dict[str, Any]:
        """Perform semantic vector search across persistent memory layers."""
        try:
            payload: Dict[str, Any] = {"query": query}
            if project:
                payload["project"] = project
            r = self.client.post("/search", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error executing search: {e}") from e

    def add_fact(self, content: str) -> Dict[str, Any]:
        """Record an immutable, discrete, version-tracked verified fact."""
        try:
            r = self.client.post("/facts", json={"content": content})
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error adding fact: {e}") from e

    def get_facts(self, include_superseded: bool = False, min_energy: float = 0.0) -> List[Fact]:
        """Fetch the active facts ledger, filtered by minimum energy score."""
        try:
            params: Dict[str, Any] = {"include_superseded": include_superseded}
            if min_energy > 0.0:
                params["min_energy"] = min_energy
            r = self.client.get("/facts", params=params)
            _handle_response_error(r)
            data = r.json()
            return data.get("facts", [])
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error retrieving facts: {e}") from e

    def get_context(self, query: Optional[str] = None, target: str = "agents") -> str:
        """Retrieve pre-compiled markdown context tailored for specific agent targets."""
        try:
            params = {"target": target}
            if query:
                params["query"] = query
            r = self.client.get("/export/persona", params=params)
            _handle_response_error(r)
            return r.text
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error retrieving context: {e}") from e

    def get_graph_data(self) -> GraphData:
        """Fetch raw D3-ready graph topology (nodes and links) from Layer 4 Neo4j."""
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
            payload: Dict[str, Any] = {"text": text, "source": source}
            if filename:
                payload["filename"] = filename
            r = self.client.post("/ingest", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error ingesting document: {e}") from e

    def get_cognitive_state(self) -> CognitiveState:
        """Retrieve current user cognitive workload and response calibration state."""
        try:
            r = self.client.get("/state")
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error retrieving cognitive state: {e}") from e

    def update_cognitive_state(
        self,
        mode: Optional[str] = None,
        urgency: Optional[float] = None,
        stress: Optional[float] = None,
        valence: Optional[float] = None,
        response_calibration: Optional[Dict[str, Any]] = None,
        recent_context_tags: Optional[List[str]] = None,
    ) -> CognitiveState:
        """Update user cognitive calibration (mode, urgency, stress, brevity, tone)."""
        payload: Dict[str, Any] = {}
        if mode is not None:
            payload["current_mode"] = mode
        if urgency is not None:
            payload["urgency_level"] = urgency
        if stress is not None:
            payload["stress_level"] = stress
        if valence is not None:
            payload["valence"] = valence
        if response_calibration is not None:
            payload["response_calibration"] = response_calibration
        if recent_context_tags is not None:
            payload["recent_context_tags"] = recent_context_tags

        try:
            r = self.client.post("/state/update", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error updating cognitive state: {e}") from e

    def run_dream_cycle(
        self, half_life_days: float = 14.0, archive_threshold: float = 0.25
    ) -> DreamReport:
        """Trigger the nightly cognitive consolidation pass (Dream Cycle)."""
        try:
            payload = {
                "half_life_days": half_life_days,
                "archive_threshold": archive_threshold,
            }
            r = self.client.post("/dream/run", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error running dream cycle: {e}") from e

    def apply_decay(
        self, half_life_days: float = 14.0, archive_threshold: float = 0.25
    ) -> MemoryDecayReport:
        """Apply synaptic memory heat decay across all active facts and nodes."""
        try:
            payload = {
                "half_life_days": half_life_days,
                "archive_threshold": archive_threshold,
            }
            r = self.client.post("/decay/apply", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error applying memory decay: {e}") from e


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
        """Close underlying async HTTP client connection pool."""
        await self.client.aclose()

    async def health(self) -> HealthStatus:
        """Query cognitive substrate health status and layer connectivity."""
        try:
            r = await self.client.get("/health")
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(
                f"Cannot connect to Friday server at {self.base_url}: {e}"
            ) from e

    async def add_memory(self, content: str, project: str = "default") -> MemoryResult:
        """Store conversational or episodic memory, triggering autonomous graph extraction."""
        try:
            r = await self.client.post("/add", json={"content": content, "project": project})
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error storing memory: {e}") from e

    async def search(self, query: str, project: Optional[str] = None) -> Dict[str, Any]:
        """Perform semantic vector search across persistent memory layers."""
        try:
            payload: Dict[str, Any] = {"query": query}
            if project:
                payload["project"] = project
            r = await self.client.post("/search", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error executing search: {e}") from e

    async def add_fact(self, content: str) -> Dict[str, Any]:
        """Record an immutable, discrete, version-tracked verified fact."""
        try:
            r = await self.client.post("/facts", json={"content": content})
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error adding fact: {e}") from e

    async def get_facts(
        self, include_superseded: bool = False, min_energy: float = 0.0
    ) -> List[Fact]:
        """Fetch the active facts ledger, filtered by minimum energy score."""
        try:
            params: Dict[str, Any] = {"include_superseded": include_superseded}
            if min_energy > 0.0:
                params["min_energy"] = min_energy
            r = await self.client.get("/facts", params=params)
            _handle_response_error(r)
            data = r.json()
            return data.get("facts", [])
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error retrieving facts: {e}") from e

    async def get_context(self, query: Optional[str] = None, target: str = "agents") -> str:
        """Retrieve pre-compiled markdown context tailored for specific agent targets."""
        try:
            params = {"target": target}
            if query:
                params["query"] = query
            r = await self.client.get("/export/persona", params=params)
            _handle_response_error(r)
            return r.text
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error retrieving context: {e}") from e

    async def get_graph_data(self) -> GraphData:
        """Fetch raw D3-ready graph topology (nodes and links) from Layer 4 Neo4j."""
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
            payload: Dict[str, Any] = {"text": text, "source": source}
            if filename:
                payload["filename"] = filename
            r = await self.client.post("/ingest", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error ingesting document: {e}") from e

    async def get_cognitive_state(self) -> CognitiveState:
        """Retrieve current user cognitive workload and response calibration state."""
        try:
            r = await self.client.get("/state")
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error retrieving cognitive state: {e}") from e

    async def update_cognitive_state(
        self,
        mode: Optional[str] = None,
        urgency: Optional[float] = None,
        stress: Optional[float] = None,
        valence: Optional[float] = None,
        response_calibration: Optional[Dict[str, Any]] = None,
        recent_context_tags: Optional[List[str]] = None,
    ) -> CognitiveState:
        """Update user cognitive calibration (mode, urgency, stress, brevity, tone)."""
        payload: Dict[str, Any] = {}
        if mode is not None:
            payload["current_mode"] = mode
        if urgency is not None:
            payload["urgency_level"] = urgency
        if stress is not None:
            payload["stress_level"] = stress
        if valence is not None:
            payload["valence"] = valence
        if response_calibration is not None:
            payload["response_calibration"] = response_calibration
        if recent_context_tags is not None:
            payload["recent_context_tags"] = recent_context_tags

        try:
            r = await self.client.post("/state/update", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error updating cognitive state: {e}") from e

    async def run_dream_cycle(
        self, half_life_days: float = 14.0, archive_threshold: float = 0.25
    ) -> DreamReport:
        """Trigger the nightly cognitive consolidation pass (Dream Cycle)."""
        try:
            payload = {
                "half_life_days": half_life_days,
                "archive_threshold": archive_threshold,
            }
            r = await self.client.post("/dream/run", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error running dream cycle: {e}") from e

    async def apply_decay(
        self, half_life_days: float = 14.0, archive_threshold: float = 0.25
    ) -> MemoryDecayReport:
        """Apply synaptic memory heat decay across all active facts and nodes."""
        try:
            payload = {
                "half_life_days": half_life_days,
                "archive_threshold": archive_threshold,
            }
            r = await self.client.post("/decay/apply", json=payload)
            _handle_response_error(r)
            return r.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise FridayConnectionError(f"Network error applying memory decay: {e}") from e
