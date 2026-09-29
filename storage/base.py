"""Storage contract independent of host files and remote transport."""

from __future__ import annotations

from typing import Protocol

from storage.models import Record


class Storage(Protocol):
    """Durable project-scoped records and atomic migration batches."""

    def list(self, kind: str, project: str) -> list[dict]: ...
    def add(self, kind: str, project: str, content: str, **fields) -> dict: ...
    def search(self, project: str, query: str, limit: int = 5) -> list[dict]: ...
    def import_records(self, records: list[Record], apply: bool = False) -> int: ...
