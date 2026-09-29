"""Lossless, conflict-rejecting snapshot import. Console output is metadata only."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from storage import from_environment
from storage.models import KINDS, LEGACY_PROJECT, Record, identifier


def read_snapshot(source: Path) -> list[Record]:
    """Verify manifest digest and validate every record before connecting."""
    manifest = json.loads((source / "manifest.json").read_text())
    raw = (source / "snapshot.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["sha256"]["snapshot.json"]:
        raise ValueError("Snapshot checksum mismatch")
    data = json.loads(raw)
    records = []
    seen = set()
    for kind in KINDS:
        for item in data[kind]:
            project = item.get("project") or LEGACY_PROJECT
            rid = item.get("id")
            if kind == "blueprints":
                rid = rid or identifier(project, item["filename"])
            if kind == "states":
                rid = "current"
            r = Record(kind, project, rid, item)
            r.validate()
            key = (kind, project, rid)
            if key in seen:
                raise ValueError("Duplicate source identity")
            seen.add(key)
            records.append(r)
    for kind, count_key in [
        ("facts", "facts_count"),
        ("memories", "memory_count"),
        ("entities", "entity_count"),
        ("edges", "edge_count"),
        ("blueprints", "blueprint_count"),
    ]:
        if len(data[kind]) != manifest[count_key]:
            raise ValueError("Manifest count mismatch")
    return records


def main():
    """Validate offline, or explicitly apply/verify a configured destination."""
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    p.add_argument("--check-destination", action="store_true")
    p.add_argument("--initialize-schema", action="store_true")
    args = p.parse_args()
    os.umask(0o077)
    try:
        records = read_snapshot(args.source)
        for kind in KINDS:
            print(f"{kind.upper()}_TO_IMPORT={sum(r.kind == kind for r in records)}")
        print("INVALID_RECORDS=0")
        if args.dry_run and not args.check_destination:
            print("CONFLICTS=NOT_CHECKED_OFFLINE\nDRY_RUN=PASS_SOURCE_ONLY")
            return
        if args.dry_run and args.initialize_schema:
            raise ValueError("Dry run cannot initialize schema")
        db = from_environment(initialize=args.initialize_schema and args.apply)
        # Always revalidate destination before writing, even after offline dry run.
        missing = db.import_records(records, apply=args.apply)
        print("CONFLICTS=0")
        if args.verify and missing:
            raise ValueError("Destination is missing source records")
        print(f"RECORDS_INSERTED={missing if args.apply else 0}")
        print("DUPLICATES_CREATED=0")
        print("VERIFY=PASS" if args.verify else "APPLY=PASS" if args.apply else "DRY_RUN=PASS")
    except Exception as exc:
        # Never print driver errors: they can contain SQL parameters / memory.
        print(f"MIGRATION=FAIL\nERROR_CLASS={type(exc).__name__}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
