"""
Friday — MCP Server (Model Context Protocol)

Exposes Friday's cognitive memory as 4 tools any AI agent can call:
  - add_memory       : Store a new memory
  - add_fact         : Store a discrete versioned fact
  - memory_search    : Semantic search across memories
  - get_context      : Get full project context (facts + recent memories)

Compatible with: Cursor, Antigravity IDE, Claude Desktop, VS Code (Cline/Roo).

Usage:
  python -m mcp.server

Add to your IDE config:
  {
    "command": "python",
    "args": ["-m", "mcp.server"],
    "env": { "FRIDAY_URL": "http://localhost:8000", "BRAIN_API_KEY": "your_key" }
  }
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from typing import Any

import httpx

logger = logging.getLogger("friday.mcp")

FRIDAY_URL: str = os.getenv("FRIDAY_URL", "http://localhost:8000")
API_KEY: str = os.getenv("FRIDAY_API_KEY") or os.getenv("BRAIN_API_KEY", "change_me")
HEADERS = {"X-Friday-Key": API_KEY, "X-Brain-Key": API_KEY, "Content-Type": "application/json"}


# ── MCP Protocol Helpers ───────────────────────────────────────────────────────
def _respond(result: Any, req_id: Any = None) -> None:
    """Write a JSON-RPC 2.0 result to stdout."""
    res = {"jsonrpc": "2.0", "result": result}
    if req_id is not None:
        res["id"] = req_id
    sys.stdout.write(json.dumps(res) + "\n")
    sys.stdout.flush()


def _error(code: int, message: str, req_id: Any = None) -> None:
    err = {"jsonrpc": "2.0", "error": {"code": code, "message": message}}
    if req_id is not None:
        err["id"] = req_id
    sys.stdout.write(json.dumps(err) + "\n")
    sys.stdout.flush()


def request_headers() -> dict:
    """Refresh IAM identity when explicitly enabled; never print credentials."""
    headers = dict(HEADERS)
    if os.getenv("FRIDAY_GCP_IAM") == "true":
        token = subprocess.check_output(
            [os.getenv("FRIDAY_GCLOUD", "gcloud"), "auth", "print-identity-token"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        headers["X-Serverless-Authorization"] = "Bearer " + token
    return headers


# ── Tool Definitions ───────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "add_memory",
        "description": "Store a memory (architecture decision, preference, bug fix, feature summary) in Friday's persistent cognitive layer.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The memory text to store."},
                "project": {
                    "type": "string",
                    "description": "Project name (e.g. 'MyApp')",
                    "default": "default",
                },
                "source": {
                    "type": "string",
                    "description": "Origin: agent | user | system",
                    "default": "agent",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "add_fact",
        "description": "Store a discrete, versioned fact (user preference, constant, rule). Facts persist forever and are deduplicated with auto-conflict resolution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The fact to store. Keep it short and atomic.",
                },
                "project": {
                    "type": "string",
                    "description": "Project namespace (e.g. 'reeldm', 'friday', 'global').",
                    "default": "global",
                },
                "supersedes": {
                    "type": "string",
                    "description": "Optional fact ID to explicitly supersede.",
                    "default": "",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "memory_search",
        "description": "Search Friday's memory for relevant context. Use before answering architecture questions or starting tasks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query."},
                "top_k": {
                    "type": "integer",
                    "description": "Number of results (1-20)",
                    "default": 5,
                },
                "project": {
                    "type": "string",
                    "description": "Optional project filter.",
                    "default": "",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_context",
        "description": "Get full Friday context: all active facts + recent memories filtered by project. Call at session start for maximum intelligence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Optional project namespace filter.",
                    "default": "",
                },
            },
        },
    },
    {
        "name": "get_blast_radius",
        "description": "Analyze the blast radius of modifying a service, table, or component across the knowledge graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity": {
                    "type": "string",
                    "description": "The name of the entity/component to analyze (e.g. 'StripeWebhook', 'UserTable').",
                },
                "depth": {
                    "type": "integer",
                    "description": "Traversal depth (hops 1-4). Default 2.",
                    "default": 2,
                },
                "project": {
                    "type": "string",
                    "description": "Optional project namespace filter.",
                    "default": "",
                },
            },
            "required": ["entity"],
        },
    },
]


# Every tool carries a project namespace. Existing callers retain default.
for tool in TOOLS:
    tool["inputSchema"]["properties"]["project"] = {
        "type": "string",
        "minLength": 1,
        "default": "default",
        "description": "Project namespace; legacy unscoped exports use __legacy_unscoped__.",
    }


# ── Tool Implementations ────────────────────────────────────────────────────────
async def add_memory(args: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{FRIDAY_URL}/add",
            headers=request_headers(),
            json={
                "content": args["content"],
                "project": args.get("project", "default"),
                "source": args.get("source", "agent"),
            },
        )
        r.raise_for_status()
        return r.json()


async def add_fact(args: dict) -> dict:
    payload = {"content": args["content"]}
    if args.get("project"):
        payload["project"] = args["project"]
    if args.get("supersedes"):
        payload["supersedes"] = args["supersedes"]
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{FRIDAY_URL}/facts", headers=request_headers(), json=payload)
        r.raise_for_status()
        return r.json()


async def get_blast_radius(args: dict) -> dict:
    params = {"entity": args["entity"], "depth": args.get("depth", 2)}
    if args.get("project"):
        params["project"] = args["project"]
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{FRIDAY_URL}/graph/blast-radius",
            headers=request_headers(),
            params=params,
        )
        r.raise_for_status()
        return r.json()


async def memory_search(args: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{FRIDAY_URL}/search",
            headers=request_headers(),
            json={
                "query": args["query"],
                "top_k": args.get("top_k", 5),
                "project": args.get("project") or "default",
            },
        )
        r.raise_for_status()
        return r.json()


async def get_context(args: dict) -> dict:
    """Read authenticated project context; preserve compatibility with legacy API."""
    async with httpx.AsyncClient(timeout=30) as client:
        params = {"project": args.get("project") or "default"}
        response = await client.get(
            f"{FRIDAY_URL}/context", headers=request_headers(), params=params
        )
        if response.status_code == 404:
            response = await client.get(
                f"{FRIDAY_URL}/facts", headers=request_headers(), params=params
            )
        response.raise_for_status()
        return response.json()


TOOL_HANDLERS = {
    "add_memory": add_memory,
    "add_fact": add_fact,
    "memory_search": memory_search,
    "get_context": get_context,
    "get_blast_radius": get_blast_radius,
}


# ── MCP Main Loop ──────────────────────────────────────────────────────────────
async def main():
    logger.info(f"Friday MCP Server started. Friday URL: {FRIDAY_URL}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = msg.get("method", "")
        req_id = msg.get("id")

        if method == "initialize":
            _respond(
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "friday", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                },
                req_id=req_id,
            )

        elif method == "notifications/initialized":
            continue

        elif method == "tools/list":
            _respond({"tools": TOOLS}, req_id=req_id)

        elif method == "tools/call":
            tool_name = msg.get("params", {}).get("name", "")
            arguments = msg.get("params", {}).get("arguments", {})
            handler = TOOL_HANDLERS.get(tool_name)
            if not handler:
                _error(-32601, f"Unknown tool: {tool_name}", req_id=req_id)
                continue
            try:
                result = await handler(arguments)
                _respond(
                    {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
                    req_id=req_id,
                )
            except Exception as e:
                _error(-32603, str(e), req_id=req_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
