"""Read a live SQLite Friday container without writing to its filesystem.

The SQLite read transaction includes WAL data. JSON files are read twice to
detect concurrent file changes. Cross-store snapshots still require a final
owner-controlled quiet period before cutover. Snapshot details stay in the
private export directory; stdout reports only completion status.
"""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

READER = r"""
import json, sqlite3, pathlib, sys
root = pathlib.Path(sys.argv[1])
database = root / sys.argv[2]
def files():
    paths = [root/'facts.json', root/'cognitive_state.json',
             pathlib.Path('/app/core/cognitive_state.json')]
    paths += sorted((root/'blueprints').glob('*'))
    return {str(p): p.read_text() for p in paths if p.is_file()}
before = files()
c = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
c.row_factory = sqlite3.Row
c.execute('BEGIN')
memories = [dict(r) for r in c.execute('SELECT * FROM memories ORDER BY id')]
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
c.rollback()
c.close()
assert all(t == 'memories' or t.startswith(('memories_fts', 'sqlite_')) for t in tables), 'Unknown source tables require export support'
after = files()
assert before == after, 'Source JSON changed during export; retry'
facts = json.loads(before.get(str(root/'facts.json'), '{"facts":[]}'))['facts']
states = [json.loads(v) for k,v in before.items() if k.endswith('cognitive_state.json')]
assert len(states) <= 1, 'Multiple cognitive states need explicit reconciliation'
blueprints = [{'filename': pathlib.Path(k).name, 'content': v} for k,v in before.items() if '/blueprints/' in k]
print(json.dumps({'facts':facts,'memories':memories,'states':states,
 'blueprints':blueprints,'entities':[],'edges':[], 'source_tables':tables}))
"""


def main():
    """Capture a private export, refusing to overwrite an existing snapshot."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", required=True)
    parser.add_argument("--data-root", type=Path, default=Path("/app/data"))
    parser.add_argument("--database-name", default="friday_memory.db")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if Path(__file__).resolve().parents[2] in (
        args.output.resolve(),
        *args.output.resolve().parents,
    ):
        raise SystemExit("Exports must be outside the migration repository")
    os.umask(0o077)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=True)
    args.output.chmod(0o700)
    if any(args.output.iterdir()):
        raise SystemExit("Refusing to overwrite a nonempty export directory")
    data = json.loads(
        subprocess.check_output(
            [
                "docker",
                "exec",
                "-i",
                args.container,
                "python",
                "-c",
                READER,
                str(args.data_root),
                args.database_name,
            ],
            stderr=subprocess.PIPE,
        )
    )
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2).encode()
    with (args.output / "snapshot.json").open("xb") as f:
        f.write(raw)
    manifest = {
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "facts_count": len(data["facts"]),
        "memory_count": len(data["memories"]),
        "entity_count": len(data["entities"]),
        "edge_count": len(data["edges"]),
        "blueprint_count": len(data["blueprints"]),
        "cognitive_state_present": bool(data["states"]),
        "sha256": {"snapshot.json": hashlib.sha256(raw).hexdigest()},
        "graph_source": "not exported by this SQLite adapter",
        "snapshot_consistency": "SQLite transaction; JSON change detection; not cross-store atomic",
    }
    with (args.output / "manifest.json").open("x") as f:
        json.dump(manifest, f, indent=2)
    print("PRIVATE_SNAPSHOT_EXPORT=PASS")


if __name__ == "__main__":
    main()
