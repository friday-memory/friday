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
from .types import Fact, GraphData, HealthStatus, MemoryResult, SearchResult

__version__ = "1.2.0"

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
    "__version__",
]
