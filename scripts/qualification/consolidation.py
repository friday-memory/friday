"""Verify scheduled job effects in the existing disposable HTTP namespace."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipelines.dream_cycle import synthesize_recent_insights
from storage import from_environment


def main():
    if "friday-migration-test-" not in os.environ["TURSO_DATABASE_URL"]:
        raise ValueError("Qualification database required")
    evidence = json.loads(
        (Path.home() / "friday-migration-data/cloud-persistence.json").read_text()
    )
    project = evidence["project"]
    assert project.startswith("qualification-http-")
    db = from_environment()
    facts = db.list("facts", project)
    assert facts and all(f.get("decay_applied_at") for f in facts)
    insights = synthesize_recent_insights(facts)
    assert insights
    memories = db.list("memories", project)
    assert all(
        any(m["content"] == insight and m["source"] == "dream_cycle" for m in memories)
        for insight in insights
    )
    edges = db.list("edges", project)
    assert any(e.get("label") == "CRYSTALLIZED_INTO" for e in edges)
    print(
        "CONSOLIDATION_DURABLE_FACTS=PASS\nCONSOLIDATION_DURABLE_INSIGHTS=PASS\nCONSOLIDATION_DURABLE_GRAPH=PASS"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("CONSOLIDATION_QUALIFICATION=FAIL\nERROR_CLASS=" + type(exc).__name__)
        raise SystemExit(1) from None
