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
from .rules import (
    AgentTarget,
    generate_all_rules,
    generate_rule_file,
    get_supported_agents,
    register_custom_agent,
    render_rule,
)
from .types import (
    BlastRadiusResult,
    CognitiveState,
    DreamReport,
    Fact,
    GraphData,
    HealthStatus,
    MemoryDecayReport,
    MemoryResult,
    SearchResult,
)

__version__ = "1.5.1"

__all__ = [
    "Friday",
    "AsyncFriday",
    "FridayError",
    "FridayConnectionError",
    "FridayAuthenticationError",
    "FridayNotFoundError",
    "FridayAPIError",
    "Fact",
    "BlastRadiusResult",
    "MemoryResult",
    "SearchResult",
    "HealthStatus",
    "GraphData",
    "CognitiveState",
    "DreamReport",
    "MemoryDecayReport",
    "AgentTarget",
    "get_supported_agents",
    "register_custom_agent",
    "render_rule",
    "generate_rule_file",
    "generate_all_rules",
    "__version__",
]
