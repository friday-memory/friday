"""Friday — Persistent Cognitive Memory Layer for AI Coding Agents.

Official Python SDK for self-hosted Friday cognitive memory server.
"""

from .client import AsyncFriday, Friday
from .exceptions import (
    FridayAPIError,
    FridayAuthenticationError,
    FridayConnectionError,
    FridayError,
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
    SearchResult,
)

__version__ = "1.3.0"

__all__ = [
    "Friday",
    "AsyncFriday",
    "FridayError",
    "FridayConnectionError",
    "FridayAuthenticationError",
    "FridayNotFoundError",
    "FridayAPIError",
    "Fact",
    "MemoryResult",
    "SearchResult",
    "HealthStatus",
    "GraphData",
    "CognitiveState",
    "DreamReport",
    "MemoryDecayReport",
    "__version__",
]
