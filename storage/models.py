"""Lossless records; source payloads retain IDs, timestamps and metadata."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

KINDS = ("facts", "memories", "entities", "edges", "blueprints", "states")
LEGACY_PROJECT = "__legacy_unscoped__"


def canonical(value: Any) -> str:
    """Stable serialization for verification and conflict detection."""
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def identifier(*parts: str) -> str:
    """Derive an unambiguous project-scoped identifier."""
    return hashlib.sha256(canonical(parts).encode()).hexdigest()


@dataclass(frozen=True)
class Record:
    """Store original source data inside an explicit namespace envelope."""

    kind: str
    project: str
    id: str
    data: dict

    def validate(self) -> None:
        """Reject malformed envelopes before opening a write transaction."""
        if (
            self.kind not in KINDS
            or not self.project
            or not self.id
            or not isinstance(self.data, dict)
        ):
            raise ValueError("Invalid record envelope")
        if self.kind in ("facts", "memories", "blueprints") and not isinstance(
            self.data.get("content"), str
        ):
            raise ValueError("Missing record content")
        canonical(self.data)
