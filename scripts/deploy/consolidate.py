"""Scheduled Cloud Run Job entrypoint. No API key in Scheduler configuration."""

from pipelines.dream_cycle import synthesize_recent_insights
from storage import from_environment


def main():
    """Consolidate each existing project with durable, deduplicated writes."""
    db = from_environment()
    projects = sorted({r.project for r in db.export_records()})
    for project in projects:
        db.decay(project)
        for insight in synthesize_recent_insights(db.list("facts", project)):
            db.add("memories", project, insight, source="dream_cycle")
            db.graph_edge(project, "Friday", insight, "CRYSTALLIZED_INTO")
    print(f"PROJECTS_CONSOLIDATED={len(projects)}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit("CONSOLIDATION=FAIL") from None
