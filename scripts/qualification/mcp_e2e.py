"""Run real stdio MCP against a configured candidate; output only pass/fail."""

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from storage import from_environment


def main():
    """Write qualification records through all four tools and verify storage."""
    if "friday-migration-test-" not in os.environ["TURSO_DATABASE_URL"]:
        raise SystemExit("MCP writes require qualification DB")
    project = "qualification-mcp-" + uuid.uuid4().hex
    calls = [
        ("add_memory", {"content": "mcp durable fixture"}),
        ("add_fact", {"content": "mcp durable fact"}),
        ("memory_search", {"query": "durable"}),
        ("get_context", {}),
    ]
    messages = [{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}}]
    messages += [
        {
            "jsonrpc": "2.0",
            "id": i + 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": dict(args, project=project)},
        }
        for i, (name, args) in enumerate(calls)
    ]
    result = subprocess.run(
        [sys.executable, "-m", "mcp.server"],
        input="".join(json.dumps(m) + "\n" for m in messages),
        text=True,
        capture_output=True,
        timeout=120,
        check=True,
    )
    responses = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(responses) == 5 and all("error" not in r for r in responses)
    payloads = [json.loads(r["result"]["content"][0]["text"]) for r in responses[1:]]
    assert payloads[0]["status"] == "added" and payloads[1]["status"] == "added"
    assert payloads[2]["results"] and payloads[3]["facts"] and payloads[3]["memories"]
    db = from_environment()
    assert len(db.list("memories", project)) == 1 and len(db.list("facts", project)) == 1
    print("MCP_TOOLS=4\nMCP_COMPATIBILITY=PASS\nMCP_REMOTE_WRITE_VERIFIED=PASS")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("MCP_COMPATIBILITY=FAIL\nERROR_CLASS=" + type(exc).__name__)
        raise SystemExit(1) from None
