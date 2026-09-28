"""Parallel Friday gateway backed entirely by SQLite or remote libSQL.

All routes except /health require an API key. Cloud Run additionally requires
IAM invocation; use X-Serverless-Authorization for IAM alongside X-Friday-Key.
"""

import hmac
import os
from copy import deepcopy

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from orchestrator.cognitive_state import DEFAULT_STATE
from storage import from_environment


class Content(BaseModel):
    """Project-scoped write with bounded content."""

    project: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=100000)
    source: str = "agent"


class Search(BaseModel):
    """Project-scoped keyword query."""

    project: str = Field(min_length=1)
    query: str = Field(min_length=1, max_length=10000)
    top_k: int = Field(5, ge=1, le=100)


class StateUpdate(BaseModel):
    """Validated cognitive-state fields."""

    project: str = Field(min_length=1)
    current_mode: str | None = None
    urgency_level: float | None = Field(None, ge=0, le=1)
    stress_level: float | None = Field(None, ge=0, le=1)
    valence: float | None = Field(None, ge=0, le=1)
    summary: str | None = None
    response_calibration: dict | None = None
    recent_context_tags: list[str] | None = None


class Blueprint(BaseModel):
    """Blueprint stored as data, never interpreted as a filesystem path."""

    project: str = Field(min_length=1)
    filename: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=1000000)


class Node(BaseModel):
    """Project-scoped graph entity."""

    project: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=500)


class Edge(BaseModel):
    """Project-scoped relationship."""

    project: str = Field(min_length=1)
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    label: str = Field("RELATES_TO", min_length=1)


class Decay(BaseModel):
    """Bounded consolidation controls."""

    project: str = Field(min_length=1)
    half_life_days: float = Field(14, gt=0)
    archive_threshold: float = Field(0.25, ge=0, le=2)


class Mutation(BaseModel):
    """Project-bound memory mutation."""

    project: str = Field(min_length=1)
    memory_id: str = Field(min_length=1)
    content: str | None = Field(None, min_length=1, max_length=100000)
    source: str | None = None


class Supersession(BaseModel):
    """Replace an existing memory in the same namespace."""

    project: str = Field(min_length=1)
    old_id: str = Field(min_length=1)
    new_content: str = Field(min_length=1, max_length=100000)
    source: str = "agent"


def create_app(store=None, api_key=None):
    """Build a fail-closed gateway without touching legacy files or services."""
    key = api_key or os.getenv("FRIDAY_API_KEY") or os.getenv("BRAIN_API_KEY")
    if not key or key in ("change_me", "change_me_in_dotenv"):
        raise RuntimeError("An explicit private API key is required")
    db = store or from_environment()
    app = FastAPI(
        title="Friday serverless candidate", docs_url=None, redoc_url=None, openapi_url=None
    )

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        if request.url.path != "/health":
            supplied = request.headers.get("X-Friday-Key") or request.headers.get("X-Brain-Key")
            if not supplied:
                auth = request.headers.get("Authorization", "")
                supplied = auth[7:] if auth.startswith("Bearer ") else ""
            if not hmac.compare_digest(supplied.encode(), key.encode()):
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        try:
            return await call_next(request)
        except Exception:
            return JSONResponse({"detail": "Storage operation failed"}, status_code=503)

    @app.get("/health")
    def health():
        """Report availability without exposing private counts or errors."""
        try:
            db.list("states", "__health__")
        except Exception:
            raise HTTPException(503, "Storage unavailable") from None
        return {"status": "healthy", "layers": {"storage": "ok"}}

    @app.post("/facts")
    def add_fact(payload: Content):
        """Add a fact within its project."""
        return db.add("facts", payload.project, payload.content)

    @app.get("/facts")
    def facts(project: str = Query(..., min_length=1), include_superseded: bool = False):
        """Retrieve only the requested project's facts."""
        items = db.list("facts", project)
        if not include_superseded:
            items = [f for f in items if not f.get("superseded") and f.get("status") != "decayed"]
        return {"total": len(items), "facts": items}

    @app.post("/add")
    def add(payload: Content):
        """Persist a memory before acknowledging the write."""
        return db.add("memories", payload.project, payload.content, source=payload.source)

    @app.post("/search")
    def search(payload: Search):
        """Retrieve project-local keyword matches."""
        return {"results": db.search(payload.project, payload.query, payload.top_k)}

    @app.get("/state")
    def state(project: str = Query(..., min_length=1)):
        """Read persisted state; default is explicitly synthetic until updated."""
        items = db.list("states", project)
        return items[0] if items else deepcopy(DEFAULT_STATE)

    @app.post("/state/update")
    def state_update(payload: StateUpdate):
        """Atomically merge state in the selected durable backend."""
        return db.update_state(
            payload.project, payload.model_dump(exclude_none=True, exclude={"project"})
        )

    @app.post("/ingest")
    def ingest(payload: Blueprint):
        """Ingest full blueprint text in durable storage."""
        return db.ingest(payload.project, payload.filename, payload.text)

    @app.get("/blueprints")
    def blueprints(project: str = Query(..., min_length=1)):
        """List project blueprints."""
        return {"blueprints": db.list("blueprints", project)}

    @app.get("/api/graph-data")
    def graph(project: str = Query(..., min_length=1)):
        """Return nodes and edges confined to one project."""
        return {"nodes": db.list("entities", project), "links": db.list("edges", project)}

    @app.post("/api/node/create")
    def node(payload: Node):
        """Create a graph node."""
        return db.graph_node(payload.project, payload.name)

    @app.post("/api/link/create")
    def edge(payload: Edge):
        """Create an edge and its endpoints atomically."""
        return db.graph_edge(payload.project, payload.source, payload.target, payload.label)

    @app.get("/api/search-quick")
    def quick(project: str = Query(..., min_length=1), q: str = ""):
        """Find project-local entities by name."""
        return {
            "results": [n for n in db.list("entities", project) if q.lower() in n["name"].lower()][
                :10
            ]
        }

    @app.get("/export/persona")
    def persona(project: str = Query(..., min_length=1)):
        """Export authenticated project context."""
        return {"facts": facts(project)["facts"], "state": state(project)}

    @app.post("/decay/apply")
    def decay(payload: Decay):
        """Persist incremental decay."""
        return db.decay(payload.project, payload.half_life_days, payload.archive_threshold)

    @app.post("/dream/run")
    def dream(payload: Decay):
        """Consolidate facts synchronously so request-based instances finish work."""
        from pipelines.dream_cycle import synthesize_recent_insights

        result = decay(payload)
        insights = synthesize_recent_insights(db.list("facts", payload.project))
        for insight in insights:
            db.add("memories", payload.project, insight, source="dream_cycle")
            db.graph_edge(payload.project, "Friday", insight, "CRYSTALLIZED_INTO")
        return dict(result, status="completed", insights_count=len(insights))

    @app.get("/context")
    def context(project: str = Query(..., min_length=1)):
        """Return facts and recent active memories for MCP."""
        memories = [m for m in db.list("memories", project) if not m.get("superseded")]
        memories.sort(key=lambda m: m.get("created_at", ""), reverse=True)
        return {"facts": facts(project)["facts"], "memories": memories[:50]}

    @app.get("/stats")
    def stats(project: str = Query(..., min_length=1)):
        """Return project-local memory counts without filesystem paths."""
        memories = db.list("memories", project)
        active = sum(not m.get("superseded") for m in memories)
        return {"total": len(memories), "active": active, "superseded": len(memories) - active}

    @app.post("/update")
    def update(payload: Mutation):
        """Update only a memory belonging to the supplied project."""
        return db.mutate_memory(
            payload.project, payload.memory_id, "update", payload.content, payload.source
        )

    @app.post("/delete")
    def delete(payload: Mutation):
        """Delete only a memory belonging to the supplied project."""
        return db.mutate_memory(payload.project, payload.memory_id, "delete")

    @app.post("/supersede")
    def supersede(payload: Supersession):
        """Atomically supersede one project's memory."""
        return db.mutate_memory(
            payload.project, payload.old_id, "supersede", payload.new_content, payload.source
        )

    return app
