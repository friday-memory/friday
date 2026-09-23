"""Friday Python SDK — Type Definitions."""

from typing import Any, Dict, List, Optional

from typing_extensions import TypedDict


class Fact(TypedDict, total=False):
    id: str
    content: str
    created_at: str
    updated_at: str
    version: int
    status: str
    source: str
    replaces: Optional[str]


class MemoryResult(TypedDict, total=False):
    status: str
    mem0_id: Optional[str]
    chroma_id: Optional[str]
    message: Optional[str]


class SearchResult(TypedDict, total=False):
    query: str
    results: Dict[str, Any]


class HealthStatus(TypedDict, total=False):
    status: str
    service: str
    version: str
    layers: Dict[str, str]
    timestamp: float


class GraphData(TypedDict, total=False):
    nodes: List[Dict[str, Any]]
    links: List[Dict[str, Any]]
