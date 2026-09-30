"""Transactional SQLite implementation shared with the remote libSQL driver."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from layers.decay import calculate_decayed_energy
from storage.models import Record, canonical, identifier


class ConflictError(ValueError):
    """A source record conflicts with a record already at the destination."""


class LocalStorage:
    """Open a fresh transaction per operation, never caching authoritative data."""

    def __init__(self, path: str, initialize: bool = True):
        self.path = path
        if path == ":memory:":
            raise ValueError("Use a temporary file; connections are per operation")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        if initialize:
            self.migrate()

    def connect(self):
        """Return a DB-API connection owned by the caller."""
        return sqlite3.connect(self.path, timeout=30)

    @contextmanager
    def transaction(self, write: bool = False):
        """Commit all writes together or roll back the entire operation."""
        c = self.connect()
        try:
            c.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    def migrate(self) -> None:
        """Apply each numbered migration exactly once, transactionally."""
        with self.transaction(True) as c:
            c.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)")
            applied = {r[0] for r in c.execute("SELECT name FROM schema_migrations").fetchall()}
            for p in sorted((Path(__file__).parent.parent / "migrations").glob("*.sql")):
                if p.name in applied:
                    continue
                statement = ""
                for line in p.read_text().splitlines(True):
                    statement += line
                    if sqlite3.complete_statement(statement):
                        c.execute(statement)
                        statement = ""
                if statement.strip():
                    raise ValueError("Incomplete migration")
                c.execute("INSERT INTO schema_migrations VALUES (?)", (p.name,))

    @staticmethod
    def _get(c, kind, project, record_id):
        row = c.execute(
            "SELECT data FROM records WHERE kind=? AND project=? AND id=?",
            (kind, project, record_id),
        ).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def _put(c, record: Record):
        record.validate()
        c.execute(
            """INSERT INTO records(kind,project,id,data,content,source,superseded)
            VALUES(?,?,?,?,?,?,?) ON CONFLICT(kind,project,id) DO UPDATE SET
            data=excluded.data,content=excluded.content,source=excluded.source,superseded=excluded.superseded""",
            (
                record.kind,
                record.project,
                record.id,
                canonical(record.data),
                record.data.get("content", record.data.get("name", "")),
                record.data.get("source", "agent"),
                int(bool(record.data.get("superseded", False))),
            ),
        )

    def list(self, kind: str, project: str) -> list[dict]:
        """Return complete source payloads for exactly one project."""
        with self.transaction() as c:
            return [
                json.loads(r[0])
                for r in c.execute(
                    "SELECT data FROM records WHERE kind=? AND project=? ORDER BY id",
                    (kind, project),
                ).fetchall()
            ]

    def export_records(self) -> list[Record]:
        """Read a consistent database snapshot for private qualification tools."""
        with self.transaction() as c:
            return [
                Record(k, p, i, json.loads(d))
                for k, p, i, d in c.execute(
                    "SELECT kind,project,id,data FROM records ORDER BY kind,project,id"
                ).fetchall()
            ]

    def import_records(self, records: list[Record], apply: bool = False) -> int:
        """Reject conflicts atomically; identical reruns create no duplicates."""
        seen = {}
        for r in records:
            r.validate()
            key = (r.kind, r.project, r.id)
            if key in seen:
                raise ConflictError("Duplicate identity in source")
            seen[key] = r
        with self.transaction(apply) as c:
            missing = []
            for r in records:
                old = self._get(c, r.kind, r.project, r.id)
                if old is not None and canonical(old) != canonical(r.data):
                    raise ConflictError("Destination conflict; no records applied")
                if old is None:
                    missing.append(r)
            if apply:
                for r in missing:
                    self._put(c, r)
            return len(missing)

    def add(self, kind: str, project: str, content: str, **fields) -> dict:
        """Deduplicate content inside its project while preserving imported IDs."""
        with self.transaction(True) as c:
            old = c.execute(
                "SELECT id FROM records WHERE kind=? AND project=? AND content=?",
                (kind, project, content),
            ).fetchone()
            if old:
                return {"status": "duplicate", "id": old[0], "fact_id": old[0]}
            rid = identifier(kind, project, content)
            data = dict(
                fields,
                id=rid,
                content=content,
                project=project,
                created_at=datetime.now(timezone.utc).isoformat(),
                superseded=False,
            )
            self._put(c, Record(kind, project, rid, data))
            return {"status": "added", "id": rid, "fact_id": rid}

    def search(self, project: str, query: str, limit: int = 5) -> list[dict]:
        """FTS5 keyword retrieval matching the deployed Porter tokenizer."""
        tokens = re.findall(r"\w+", query, re.UNICODE)
        if not tokens:
            return []
        match = " OR ".join('"' + t + '"' for t in tokens)
        with self.transaction() as c:
            return [
                dict(json.loads(d), score=abs(rank))
                for d, rank in c.execute(
                    """
                SELECT r.data, rank FROM records_fts JOIN records r ON r.rowid=records_fts.rowid
                WHERE records_fts MATCH ? AND r.kind='memories' AND r.project=?
                AND r.superseded=0 ORDER BY rank, r.id LIMIT ?""",
                    (match, project, limit),
                ).fetchall()
            ]

    def update_state(self, project: str, updates: dict) -> dict:
        """Merge cognitive state inside one serialized transaction."""
        from copy import deepcopy

        from orchestrator.cognitive_state import DEFAULT_STATE

        with self.transaction(True) as c:
            state = self._get(c, "states", project, "current") or deepcopy(DEFAULT_STATE)
            for key, value in updates.items():
                if key == "response_calibration":
                    state.setdefault(key, {}).update(value)
                elif key == "recent_context_tags":
                    state[key] = list(dict.fromkeys(value + state.get(key, [])))[:10]
                else:
                    state[key] = value
            state["last_interaction_at"] = datetime.now(timezone.utc).isoformat()
            self._put(c, Record("states", project, "current", state))
            return state

    def graph_node(self, project: str, name: str) -> dict:
        """Create a node without altering existing attributes."""
        with self.transaction(True) as c:
            self._node(c, project, name)
        return {"status": "created", "name": name}

    def _node(self, c, project, name):
        if self._get(c, "entities", project, name) is None:
            self._put(
                c, Record("entities", project, name, {"id": name, "name": name, "project": project})
            )

    def graph_edge(self, project: str, source: str, target: str, label: str) -> dict:
        """Create both endpoints and their edge in one project transaction."""
        rid = identifier(project, source, target, label)
        with self.transaction(True) as c:
            self._node(c, project, source)
            self._node(c, project, target)
            self._put(
                c,
                Record(
                    "edges",
                    project,
                    rid,
                    {
                        "id": rid,
                        "source": source,
                        "target": target,
                        "label": label,
                        "project": project,
                    },
                ),
            )
        return {"status": "linked", "id": rid}

    def ingest(self, project: str, filename: str, text: str) -> dict:
        """Persist full blueprint and searchable memory atomically; no file writes."""
        rid = identifier(project, filename)
        with self.transaction(True) as c:
            for kind in ("blueprints", "memories"):
                self._put(
                    c,
                    Record(
                        kind,
                        project,
                        rid,
                        {
                            "id": rid,
                            "filename": filename,
                            "content": text,
                            "project": project,
                            "source": "blueprint",
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        },
                    ),
                )
        return {"status": "ingested", "filename": filename, "memory_id": rid}

    def decay(self, project: str, half_life: float = 14, threshold: float = 0.25) -> dict:
        """Apply elapsed decay once; retries do not compound the full record age."""
        now = datetime.now(timezone.utc)
        count = 0
        with self.transaction(True) as c:
            rows = c.execute(
                "SELECT id,data FROM records WHERE kind='facts' AND project=?", (project,)
            ).fetchall()
            for rid, raw in rows:
                f = json.loads(raw)
                if f.get("superseded") or f.get("status") in ("superseded", "archived"):
                    continue
                f["energy_score"] = (
                    2.0
                    if f.get("decay_immune")
                    else calculate_decayed_energy(
                        f.get("energy_score", 1),
                        f.get("decay_applied_at") or f.get("last_recalled_at"),
                        f.get("created_at"),
                        half_life,
                        now,
                    )
                )
                f["status"] = "decayed" if f["energy_score"] < threshold else "active"
                f["decay_applied_at"] = now.isoformat()
                count += f["status"] == "decayed"
                self._put(c, Record("facts", project, rid, f))
        return {"evaluated_facts_count": len(rows), "decayed_facts_count": count}

    def mutate_memory(
        self, project: str, memory_id: str, action: str, content=None, source=None
    ) -> dict:
        """Update, delete, or supersede a memory without crossing projects."""
        with self.transaction(True) as c:
            old = self._get(c, "memories", project, memory_id)
            if old is None:
                return {"status": "not_found", "id": memory_id}
            if action == "delete":
                c.execute(
                    "DELETE FROM records WHERE kind='memories' AND project=? AND id=?",
                    (project, memory_id),
                )
                return {"status": "deleted", "id": memory_id}
            if action == "supersede":
                if not content or content == old["content"]:
                    raise ValueError("Supersession requires different content")
                existing = c.execute(
                    "SELECT id FROM records WHERE kind='memories' AND project=? AND content=?",
                    (project, content),
                ).fetchone()
                rid = existing[0] if existing else identifier("memories", project, content)
                replacement = self._get(c, "memories", project, rid) or {
                    "id": rid,
                    "project": project,
                    "content": content,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                replacement.update(
                    superseded=False,
                    superseded_by=None,
                    source=source or old.get("source", "agent"),
                )
                self._put(c, Record("memories", project, rid, replacement))
                old.update(superseded=True, superseded_by=rid)
            elif action == "update":
                if content is not None:
                    old["content"] = content
                if source is not None:
                    old["source"] = source
            else:
                raise ValueError("Unsupported memory mutation")
            old["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._put(c, Record("memories", project, memory_id, old))
            return {
                "status": "superseded" if action == "supersede" else "updated",
                "id": memory_id,
                "new_id": old.get("superseded_by"),
            }


    def revoke_fact(self, project: str, fact_id: str, reason: str = "") -> dict:
        """Revoke a fact by marking it superseded and revoked."""
        now = datetime.now(timezone.utc).isoformat()
        with self.transaction(True) as c:
            old = self._get(c, "facts", project, fact_id)
            if old is None:
                return {"status": "not_found", "fact_id": fact_id}
            old["superseded"] = True
            old["status"] = "revoked"
            old["revoked_at"] = now
            old["revoked_reason"] = reason or "Explicit revocation"
            self._put(c, Record("facts", project, fact_id, old))
            return {"status": "revoked", "fact_id": fact_id, "project": project}

    def delete_fact(self, project: str, fact_id: str, hard: bool = False) -> dict:
        """Permanently delete or revoke a fact from storage."""
        if not hard:
            return self.revoke_fact(project, fact_id, reason="Deleted via API")
        with self.transaction(True) as c:
            old = self._get(c, "facts", project, fact_id)
            if old is None:
                return {"status": "not_found", "fact_id": fact_id}
            c.execute(
                "DELETE FROM records WHERE kind='facts' AND project=? AND id=?",
                (project, fact_id),
            )
            return {"status": "deleted", "fact_id": fact_id, "project": project, "hard": True}
