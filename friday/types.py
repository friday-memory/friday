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
    energy_score: Optional[float]
    last_recalled_at: Optional[str]
    recall_count: Optional[int]
    decay_immune: Optional[bool]


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


class CognitiveState(TypedDict, total=False):
    current_mode: str
    urgency_level: float
    stress_level: float
    valence: float
    last_interaction_at: str
    response_calibration: Dict[str, Any]
    summary: str


class DreamReport(TypedDict, total=False):
    timestamp: str
    status: str
    pruned_ephemeral_count: int
    decayed_facts_count: int
    crystallized_insights: List[str]
    new_graph_edges_count: int
    duration_ms: float


class MemoryDecayReport(TypedDict, total=False):
    timestamp: str
    evaluated_facts_count: int
    decayed_facts_count: int
    active_facts_count: int
    half_life_days: float
