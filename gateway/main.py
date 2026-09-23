"""
Friday — Gateway (FastAPI)
The cognitive memory backbone for AI coding agents.

Endpoints:
  POST /add          - Store a memory + trigger autonomous graph wiring
  POST /facts        - Store a versioned discrete fact
  GET  /facts        - Retrieve active facts ledger
  POST /search       - Semantic memory search
  GET  /health       - System health check
  GET  /             - Neural Studio UI
  GET  /api/graph-data  - Knowledge graph data (nodes + links)
  ...and more. See /docs for full OpenAPI spec.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

load_dotenv()

# ── Configuration (all from .env) ─────────────────────────────────────────────
FRIDAY_API_KEY: str = os.getenv("FRIDAY_API_KEY") or os.getenv(
    "BRAIN_API_KEY", "change_me_in_dotenv"
)
FACTS_PATH: str = os.getenv("FACTS_PATH", "/app/facts/facts.json")
NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "change_this_strong_password")
MEM0_API_KEY: str = os.getenv("MEM0_API_KEY", "")
DEEPSEEK_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

STUDIO_PATH = Path(__file__).parent.parent / "studio" / "index.html"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("friday")

# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Friday — Cognitive Memory API",
    description="Persistent cognitive memory layer for AI coding agents.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth ───────────────────────────────────────────────────────────────────────
def verify_key(request: Request):
    key = (
        request.headers.get("X-Friday-Key")
        or request.headers.get("X-Brain-Key")
        or request.headers.get("Authorization", "").replace("Bearer ", "")
        or request.query_params.get("key")
    )
    if key != FRIDAY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid Friday Server Secret Key.")
    return key


# ── Lazy layer imports (graceful if services not yet running) ──────────────────
def get_neo4j_driver():
    try:
        from neo4j import GraphDatabase

        return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except Exception as e:
        logger.warning(f"Neo4j not available: {e}")
        return None


def get_mem0_client():
    try:
        from mem0 import MemoryClient

        return MemoryClient(api_key=MEM0_API_KEY) if MEM0_API_KEY else None
    except Exception as e:
        logger.warning(f"Mem0 not available: {e}")
        return None


# ── Pydantic Models ────────────────────────────────────────────────────────────
class MemoryPayload(BaseModel):
    content: str = Field(..., description="The memory text to store.")
    source: str = Field("agent", description="Origin: agent | user | system")
    project: str = Field("default", description="Project namespace.")


class FactPayload(BaseModel):
    content: str = Field(..., description="A discrete, versioned fact.")


class SearchPayload(BaseModel):
    query: str = Field(..., description="Natural language search query.")
    top_k: int = Field(5, ge=1, le=20)
    project: str = Field("", description="Optional project filter.")


# ── Facts File (S3-style versioned ledger) ─────────────────────────────────────
def _load_facts() -> dict:
    p = Path(FACTS_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"facts": []}


def _save_facts(data: dict):
    Path(FACTS_PATH).write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def studio():
    """Serve the Neural Studio UI."""
    if STUDIO_PATH.exists():
        return HTMLResponse(content=STUDIO_PATH.read_text(), status_code=200)
    return HTMLResponse("<h1>Friday Neural Studio</h1><p>studio/index.html not found.</p>")


@app.get("/health")
async def health():
    """Health check — verifies all layers."""
    layers = {}

    # Neo4j check
    driver = get_neo4j_driver()
    if driver:
        try:
            with driver.session() as s:
                s.run("RETURN 1")
            layers["neo4j"] = "ok"
        except Exception as e:
            layers["neo4j"] = f"error: {e}"
        finally:
            driver.close()
    else:
        layers["neo4j"] = "unavailable"

    # Mem0 check
    mem0 = get_mem0_client()
    layers["mem0"] = "ok" if mem0 else "unavailable (check MEM0_API_KEY)"

    # Facts ledger check
    facts_data = _load_facts()
    layers["facts"] = f"ok ({len(facts_data.get('facts', []))} entries)"

    overall = "healthy" if all("ok" in str(v) for v in layers.values()) else "degraded"
    return {
        "status": overall,
        "layers": layers,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/add")
async def add_memory(
    payload: MemoryPayload, background_tasks: BackgroundTasks, _key=Depends(verify_key)
):
    """Store a memory in Mem0 + ChromaDB and trigger autonomous graph wiring."""
    results = {}

    # Store in Mem0
    mem0 = get_mem0_client()
    if mem0:
        try:
            r = mem0.add(
                payload.content,
                user_id="friday_user",
                metadata={"source": payload.source, "project": payload.project},
            )
            results["mem0_id"] = r[0].get("id") if r else None
        except Exception as e:
            results["mem0_error"] = str(e)

    # Background: auto-extract entities → Neo4j graph
    if DEEPSEEK_KEY:
        from pipelines.auto_graph import auto_extract_and_link_graph

        background_tasks.add_task(
            auto_extract_and_link_graph,
            payload.content,
            payload.project,
            NEO4J_URI,
            NEO4J_USER,
            NEO4J_PASSWORD,
            DEEPSEEK_KEY,
            DEEPSEEK_BASE,
            DEEPSEEK_MODEL,
        )

    results["status"] = "added"
    return results


@app.post("/facts")
async def add_fact(payload: FactPayload, _key=Depends(verify_key)):
    """Add a discrete, versioned fact to the ledger."""
    data = _load_facts()
    fact_id = hashlib.sha256(payload.content.encode()).hexdigest()[:12]
    now = datetime.now(timezone.utc).isoformat()

    # Supersede duplicates
    for f in data["facts"]:
        if f.get("content") == payload.content:
            return {"status": "duplicate", "fact_id": fact_id}

    data["facts"].append(
        {
            "id": fact_id,
            "content": payload.content,
            "created_at": now,
            "superseded": False,
        }
    )
    _save_facts(data)
    return {"status": "added", "fact_id": fact_id}


@app.get("/facts")
async def get_facts(include_superseded: bool = False):
    """Retrieve the active facts ledger. Public endpoint — no auth required."""
    data = _load_facts()
    facts = data.get("facts", [])
    if not include_superseded:
        facts = [f for f in facts if not f.get("superseded", False)]
    return {"total": len(facts), "facts": facts}


@app.post("/search")
async def search_memory(payload: SearchPayload, _key=Depends(verify_key)):
    """Semantic memory search across all stored memories."""
    mem0 = get_mem0_client()
    if not mem0:
        raise HTTPException(503, "Mem0 not configured. Check MEM0_API_KEY.")
    try:
        results = mem0.search(payload.query, user_id="friday_user", limit=payload.top_k)
        return {"query": payload.query, "results": results}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/ingest")
async def ingest_blueprint(
    payload: dict, background_tasks: BackgroundTasks, _key=Depends(verify_key)
):
    """Ingest a text blob (blueprint, architecture doc) into the memory system."""
    text = payload.get("text", "")
    source = payload.get("source", "blueprint")
    filename = payload.get("filename", "unnamed.md")

    if not text:
        raise HTTPException(400, "Field 'text' is required.")

    # Save to local blueprints dir
    bp_dir = Path("/app/blueprints")
    bp_dir.mkdir(parents=True, exist_ok=True)
    (bp_dir / filename).write_text(text)

    # Also store in Mem0 as memory
    mem0 = get_mem0_client()
    mem0_id = None
    if mem0:
        try:
            r = mem0.add(
                text[:2000], user_id="friday_user", metadata={"source": source, "file": filename}
            )
            mem0_id = r[0].get("id") if r else None
        except Exception:
            pass

    return {"status": "ingested", "filename": filename, "mem0_id": mem0_id}


# ── Graph API ──────────────────────────────────────────────────────────────────
@app.get("/api/graph-data")
async def graph_data():
    """Return Neo4j knowledge graph nodes and links for Neural Studio."""
    driver = get_neo4j_driver()
    if not driver:
        return {"nodes": [], "links": [], "error": "Neo4j unavailable"}
    try:
        with driver.session() as session:
            node_res = session.run(
                "MATCH (n) OPTIONAL MATCH (n)-[r]-() "
                "RETURN n.name AS name, n.id AS id, n.project AS project, "
                "n.color AS color, COUNT(r) AS degree LIMIT 500"
            )
            nodes = []
            for row in node_res:
                name = row["name"] or row["id"] or "Unknown"
                nodes.append(
                    {
                        "id": name,
                        "name": name,
                        "project": row.get("project", "default"),
                        "color": row.get("color"),
                        "degree": row["degree"],
                        "val": max(int(row["degree"]) * 2.2, 5),
                    }
                )

            link_res = session.run(
                "MATCH (a)-[r]->(b) RETURN a.name AS source, b.name AS target, "
                "type(r) AS label LIMIT 1000"
            )
            links = [
                {"source": r["source"], "target": r["target"], "label": r["label"]}
                for r in link_res
                if r["source"] and r["target"]
            ]

        return {"nodes": nodes, "links": links}
    except Exception as e:
        logger.error(f"Graph data error: {e}")
        return {"nodes": [], "links": [], "error": str(e)}
    finally:
        driver.close()


@app.post("/api/node/create")
async def create_node(payload: dict, _key=Depends(verify_key)):
    """Create a new entity node in the knowledge graph."""
    name = payload.get("name", "").strip()
    parent_id = payload.get("parent_id", "Friday")
    relation = payload.get("relation", "RELATES_TO")
    if not name:
        raise HTTPException(400, "Field 'name' required.")
    driver = get_neo4j_driver()
    if not driver:
        raise HTTPException(503, "Neo4j unavailable.")
    try:
        with driver.session() as s:
            s.run(
                "MERGE (n:Entity {name: $name}) "
                "WITH n MERGE (p:Entity {name: $parent}) "
                "MERGE (p)-[:" + relation + "]->(n)",
                name=name,
                parent=parent_id,
            )
        return {"status": "created", "name": name, "parent": parent_id}
    finally:
        driver.close()


@app.delete("/api/node/{node_id}")
async def delete_node(node_id: str, _key=Depends(verify_key)):
    """Delete an entity node and all its relationships."""
    driver = get_neo4j_driver()
    if not driver:
        raise HTTPException(503, "Neo4j unavailable.")
    try:
        with driver.session() as s:
            s.run("MATCH (n {name: $name}) DETACH DELETE n", name=node_id)
        return {"status": "deleted", "node_id": node_id}
    finally:
        driver.close()


@app.post("/api/node/rename")
async def rename_node(payload: dict, _key=Depends(verify_key)):
    old_name = payload.get("old_name", "").strip()
    new_name = payload.get("new_name", "").strip()
    if not old_name or not new_name:
        raise HTTPException(400, "Fields 'old_name' and 'new_name' required.")
    driver = get_neo4j_driver()
    if not driver:
        raise HTTPException(503, "Neo4j unavailable.")
    try:
        with driver.session() as s:
            s.run("MATCH (n {name: $old}) SET n.name = $new", old=old_name, new=new_name)
        return {"status": "renamed", "old_name": old_name, "new_name": new_name}
    finally:
        driver.close()


@app.post("/api/link/create")
async def create_link(payload: dict, _key=Depends(verify_key)):
    source = payload.get("source", "").strip()
    target = payload.get("target", "").strip()
    label = payload.get("label", "RELATES_TO").strip().upper().replace(" ", "_")
    if not source or not target:
        raise HTTPException(400, "Fields 'source' and 'target' required.")
    driver = get_neo4j_driver()
    if not driver:
        raise HTTPException(503, "Neo4j unavailable.")
    try:
        with driver.session() as s:
            s.run(
                f"MERGE (a:Entity {{name: $src}}) MERGE (b:Entity {{name: $tgt}}) MERGE (a)-[:{label}]->(b)",
                src=source,
                tgt=target,
            )
        return {"status": "linked", "source": source, "target": target, "label": label}
    finally:
        driver.close()


@app.get("/api/search-quick")
async def search_quick(q: str = ""):
    """Quick node search in the knowledge graph. Public endpoint."""
    driver = get_neo4j_driver()
    if not driver:
        return {"results": []}
    try:
        with driver.session() as s:
            result = s.run(
                "MATCH (n) WHERE toLower(n.name) CONTAINS toLower($q) "
                "RETURN n.name AS name, n.project AS project LIMIT 10",
                q=q,
            )
            results = [{"name": r["name"], "project": r.get("project", "")} for r in result]
        return {"results": results}
    finally:
        driver.close()


@app.get("/export/persona")
async def export_persona(target: str = "agents", _key=Depends(verify_key)):
    """
    Export synchronized agent persona & architectural directives.
    Targets: 'agents' (AGENTS.md / GEMINI.md), 'cursor' (.cursorrules), 'soul' (SOUL.md for chat agents).
    """
    facts_data = _load_facts()
    active_facts = [
        f["content"] for f in facts_data.get("facts", []) if f.get("status", "active") == "active"
    ]

    if target == "soul":
        lines = [
            "# Persona & Directives (SOUL.md)",
            "",
            "You are connected to Friday Central Cognitive Memory as your persistent brain.",
            "",
            "## Active System Facts",
        ]
    elif target == "cursor":
        lines = [
            "# Cursor AI Project Rules",
            "",
            "## Architecture Truths (Synced from Friday Central Brain)",
        ]
    else:
        lines = [
            "# Agent Directives & Architectural Rules",
            "",
            "> Auto-synced from Friday Central Cognitive Memory. Single Source of Truth across all agents.",
            "",
            "## Verified Architectural Facts",
        ]

    if active_facts:
        for fact in active_facts:
            lines.append(f"- {fact}")
    else:
        lines.append("- (No active facts stored in memory ledger yet)")

    lines.extend(
        [
            "",
            "## Persistent Memory Protocol (MCP)",
            "- Before refactoring major subsystems, query Friday Brain via `memory_search`.",
            "- When confirming architectural decisions, schema changes, or bug fixes, record them via `add_memory` or `add_fact`.",
            "- Zero duplicate prompt bloat: keep prompt context lean and rely on Friday for deep retrieval.",
            "",
        ]
    )

    return Response(content="\n".join(lines), media_type="text/markdown")
