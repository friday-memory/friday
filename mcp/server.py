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

import os
import sys
import json
import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger("friday.mcp")

FRIDAY_URL: str = os.getenv("FRIDAY_URL", "http://localhost:8000")
API_KEY: str    = os.getenv("FRIDAY_API_KEY") or os.getenv("BRAIN_API_KEY", "change_me")
HEADERS = {"X-Friday-Key": API_KEY, "X-Brain-Key": API_KEY, "Content-Type": "application/json"}

# ── MCP Protocol Helpers ───────────────────────────────────────────────────────
def _respond(result: Any) -> None:
    """Write a JSON-RPC 2.0 result to stdout."""
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "result": result}) + "\n")
    sys.stdout.flush()

def _error(code: int, message: str) -> None:
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "error": {"code": code, "message": message}}) + "\n")
    sys.stdout.flush()

# ── Tool Definitions ───────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "add_memory",
        "description": "Store a memory (architecture decision, preference, bug fix, feature summary) in Friday's persistent cognitive layer.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content":  {"type": "string", "description": "The memory text to store."},
                "project":  {"type": "string", "description": "Project name (e.g. 'MyApp')", "default": "default"},
                "source":   {"type": "string", "description": "Origin: agent | user | system", "default": "agent"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "add_fact",
        "description": "Store a discrete, versioned fact (user preference, constant, rule). Facts persist forever and are deduplicated.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The fact to store. Keep it short and atomic."},
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
                "query":   {"type": "string", "description": "Natural language search query."},
                "top_k":   {"type": "integer", "description": "Number of results (1-20)", "default": 5},
                "project": {"type": "string", "description": "Optional project filter.", "default": ""},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_context",
        "description": "Get full Friday context: all active facts + recent memories. Call at session start for maximum intelligence.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]

# ── Tool Implementations ────────────────────────────────────────────────────────
async def add_memory(args: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{FRIDAY_URL}/add", headers=HEADERS, json={
            "content": args["content"],
            "project": args.get("project", "default"),
            "source":  args.get("source", "agent"),
        })
        r.raise_for_status()
        return r.json()

async def add_fact(args: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{FRIDAY_URL}/facts", headers=HEADERS, json={"content": args["content"]})
        r.raise_for_status()
        return r.json()

async def memory_search(args: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{FRIDAY_URL}/search", headers=HEADERS, json={
            "query":   args["query"],
            "top_k":   args.get("top_k", 5),
            "project": args.get("project", ""),
        })
        r.raise_for_status()
        return r.json()

async def get_context(args: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        facts_r = await client.get(f"{FRIDAY_URL}/facts")
        facts = facts_r.json().get("facts", []) if facts_r.is_success else []
        return {
            "facts": facts,
            "instruction": "Use these facts as absolute truth when responding. Search memory for project-specific context.",
        }

TOOL_HANDLERS = {
    "add_memory":    add_memory,
    "add_fact":      add_fact,
    "memory_search": memory_search,
    "get_context":   get_context,
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

        if method == "initialize":
            _respond({
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "friday", "version": "1.0.0"},
                "capabilities": {"tools": {}},
            })

        elif method == "tools/list":
            _respond({"tools": TOOLS})

        elif method == "tools/call":
            tool_name = msg.get("params", {}).get("name", "")
            arguments  = msg.get("params", {}).get("arguments", {})
            handler = TOOL_HANDLERS.get(tool_name)
            if not handler:
                _error(-32601, f"Unknown tool: {tool_name}")
                continue
            try:
                result = await handler(arguments)
                _respond({"content": [{"type": "text", "text": json.dumps(result, indent=2)}]})
            except Exception as e:
                _error(-32603, str(e))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
