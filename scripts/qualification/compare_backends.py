"""Compare private source snapshot with destination without printing content."""

import argparse
import math
import os
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.migration.import_to_turso import read_snapshot
from storage import from_environment
from storage.models import KINDS, canonical


def equivalent_cutoff_ties(old: list[dict], new: list[dict], expanded: list[dict]) -> bool:
    """Accept different cutoff ties only when all changed records have equal rank."""
    if not old or len(old) != len(new):
        return False
    old_by_id = {r["id"]: r for r in old}
    new_by_id = {r["id"]: r for r in new}
    expanded_by_id = {r["id"]: r for r in expanded}
    cutoff = old[-1]["score"]
    if not math.isclose(cutoff, new[-1]["score"], rel_tol=1e-9, abs_tol=1e-15):
        return False
    for rid, row in old_by_id.items():
        candidate = expanded_by_id.get(rid)
        if (
            not candidate
            or row["content"] != candidate["content"]
            or not math.isclose(row["score"], candidate["score"], rel_tol=1e-9, abs_tol=1e-15)
        ):
            return False
    for rid in old_by_id.keys() ^ new_by_id.keys():
        row = old_by_id.get(rid) or new_by_id[rid]
        if not math.isclose(row["score"], cutoff, rel_tol=1e-9, abs_tol=1e-15):
            return False
    return True


def compare(source: Path, db, live_client=None) -> dict:
    """Compare exact payloads, counts, namespace isolation and known-token search."""
    records = read_snapshot(source)
    expected = {(r.kind, r.project, r.id): canonical(r.data) for r in records}
    actual = {(r.kind, r.project, r.id): canonical(r.data) for r in db.export_records()}
    missing = sum(actual.get(k) != v for k, v in expected.items())
    # Recreate the live memory tokenizer on an in-memory reference database.
    reference = sqlite3.connect(":memory:")
    reference.execute(
        "CREATE VIRTUAL TABLE legacy USING fts5(content, source, project, superseded UNINDEXED, tokenize='porter unicode61')"
    )
    memories = [r for r in records if r.kind == "memories"]
    for r in memories:
        reference.execute(
            "INSERT INTO legacy(content,source,project,superseded) VALUES(?,?,?,?)",
            (
                r.data["content"],
                r.data.get("source", "agent"),
                r.project,
                int(bool(r.data.get("superseded"))),
            ),
        )
    searches, differences, live_differences, tied_differences = 0, 0, 0, 0
    for project in sorted({r.project for r in memories}):
        subset = [r for r in memories if r.project == project]
        tokens = sorted(
            {t.lower() for r in subset for t in re.findall(r"\w+", r.data["content"]) if len(t) > 3}
        )[:10]
        for token in tokens:
            # Reproduce the deployed index and compare without printing query text.
            rows = reference.execute(
                "SELECT content FROM legacy WHERE legacy MATCH ? AND project=? AND superseded=0 ORDER BY rank LIMIT 5",
                ('"' + token + '"', project),
            ).fetchall()
            candidate = db.search(project, token, 5)
            differences += {r[0] for r in rows} != {r["content"] for r in candidate}
            if live_client is not None:
                response = live_client.post(
                    "/search", json={"project": project, "query": token, "top_k": 5}
                )
                response.raise_for_status()
                old = response.json()["results"]
                if {r["content"] for r in old} != {r["content"] for r in candidate}:
                    live_differences += 1
                    tied_differences += equivalent_cutoff_ties(
                        old, candidate, db.search(project, token, 1000)
                    )
            searches += 1
        if any(r.get("project", project) != project for r in db.list("memories", project)):
            raise ValueError("Project isolation failed")
    reference.close()
    result = {
        "PAYLOAD_MISMATCHES": missing,
        "EXTRA_RECORDS": len(actual.keys() - expected.keys()),
        "SEARCH_QUERIES": searches,
        "LIVE_SEARCH_DIFFERENCES": live_differences if live_client is not None else "NOT_TESTED",
        "LIVE_EQUIVALENT_CUTOFF_TIES": tied_differences,
        "SEARCH_RESULT_SET_DIFFERENCES": differences,
        "PROJECT_ISOLATION": "PASS"
        if not db.search("__nonexistent_qualification_project__", "memory")
        else "FAIL",
    }
    for kind in KINDS:
        result[kind.upper() + "_VERIFIED"] = sum(
            k[0] == kind for k in expected if actual.get(k) == expected[k]
        )
    result["PARITY"] = (
        "PASS"
        if not missing
        and not differences
        and live_differences == tied_differences
        and result["PROJECT_ISOLATION"] == "PASS"
        else "FAIL"
    )
    if result["PARITY"] == "PASS" and tied_differences:
        result["PARITY"] = "PASS_RANK_EQUIVALENT_WITH_CUTOFF_TIES"
    return result


def main():
    """Run a read-only destination comparison using private environment config."""
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    args = p.parse_args()
    try:
        source_url = os.getenv("FRIDAY_SOURCE_URL")
        if source_url:
            import httpx

            key = os.getenv("FRIDAY_SOURCE_API_KEY")
            if not key:
                raise ValueError("Missing configured source API key")
            with httpx.Client(
                base_url=source_url, headers={"X-Friday-Key": key}, timeout=30
            ) as client:
                result = compare(args.source, from_environment(), client)
        else:
            result = compare(args.source, from_environment())
        print("PARITY=" + result["PARITY"])
        raise SystemExit(0 if result["PARITY"].startswith("PASS") else 1)
    except Exception as exc:
        print("PARITY=FAIL\nERROR_CLASS=" + type(exc).__name__)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
