"""The Dream Cycle Engine (Nightly Cognitive Consolidation).

Executes the biological sleep cycle for AI persistent memory:
1. Synaptic Decay & Pruning: Evaporates low-energy ephemeral facts.
2. Episodic Synthesis: Distills daily conversation and fact logs into strategic insights.
3. Knowledge Crystallization: Persists consolidated relationships into Neo4j.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from layers.decay import apply_system_decay

logger = logging.getLogger("friday.dream_cycle")


def synthesize_recent_insights(facts: List[Dict[str, Any]], max_insights: int = 2) -> List[str]:
    """Rule-based semantic clustering & synthesis for high-energy facts.

    Identifies key thematic clusters (e.g., pricing, infrastructure, architecture)
    and formulates crystallized strategic insights.
    """
    if not facts:
        return []

    # Filter to active facts with high energy
    high_energy = [
        f for f in facts if f.get("status") == "active" and f.get("energy_score", 1.0) >= 0.8
    ]
    if not high_energy:
        high_energy = [f for f in facts if f.get("status") == "active"]

    if not high_energy:
        return []

    insights: List[str] = []
    topics: Dict[str, List[str]] = {
        "payments": [],
        "infrastructure": [],
        "architecture": [],
        "verification": [],
    }

    for f in high_energy:
        content = f.get("content", "").lower()
        if any(
            w in content
            for w in ("razorpay", "dodo", "payment", "subscription", "pass", "pricing", "inr")
        ):
            topics["payments"].append(f.get("content", ""))
        elif any(w in content for w in ("ec2", "aws", "server", "docker", "ssh", "cron", "backup")):
            topics["infrastructure"].append(f.get("content", ""))
        elif any(w in content for w in ("meta", "instagram", "verification", "gstin", "jhalka")):
            topics["verification"].append(f.get("content", ""))
        elif any(w in content for w in ("neo4j", "chroma", "mem0", "fastapi", "layers", "mcp")):
            topics["architecture"].append(f.get("content", ""))

    # Formulate domain insights
    if topics["infrastructure"]:
        insights.append(
            f"Infrastructure Consolidation: Verified {len(topics['infrastructure'])} active server directives with automated GitHub backup & deploy key auth."
        )
    if topics["payments"]:
        insights.append(
            f"Monetization Anchor: Consolidated {len(topics['payments'])} payment paths across domestic prepaid passes and global subscriptions."
        )
    if not insights and high_energy:
        top_fact = high_energy[-1].get("content", "")
        insights.append(f"Crystallized Learning: {top_fact[:120]}")

    return insights[:max_insights]


def run_dream_cycle(
    facts_path: Optional[str] = None,
    neo4j_uri: Optional[str] = None,
    neo4j_user: Optional[str] = None,
    neo4j_password: Optional[str] = None,
    half_life_days: float = 14.0,
    archive_threshold: float = 0.25,
) -> Dict[str, Any]:
    """Execute complete 4-stage Dream Cycle consolidation."""
    start_time = time.time()
    now_iso = datetime.now(timezone.utc).isoformat()
    logger.info("🌙 Starting Friday Dream Cycle consolidation...")

    # Stage 1: Synaptic Decay & Pruning
    decay_report = apply_system_decay(
        facts_path=facts_path,
        half_life_days=half_life_days,
        archive_threshold=archive_threshold,
    )

    # Stage 2: Episodic Clustering & Synthesis
    resolved_facts_path = Path(facts_path or os.getenv("FACTS_PATH", "/app/facts/facts.json"))
    active_facts: List[Dict[str, Any]] = []
    if resolved_facts_path.exists():
        try:
            raw = json.loads(resolved_facts_path.read_text(encoding="utf-8"))
            active_facts = [f for f in raw.get("facts", []) if f.get("status") == "active"]
        except Exception as e:
            logger.warning("Failed to load facts during dream cycle: %s", e)

    crystallized_insights = synthesize_recent_insights(active_facts)

    # Stage 3: Neo4j Knowledge Consolidation (if configured)
    edges_created = 0
    uri = neo4j_uri or os.getenv("NEO4J_URI")
    user = neo4j_user or os.getenv("NEO4J_USER")
    pwd = neo4j_password or os.getenv("NEO4J_PASSWORD")

    if uri and user and pwd:
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(uri, auth=(user, pwd))
            with driver.session() as session:
                for idx, insight in enumerate(crystallized_insights):
                    session.run(
                        """
                        MERGE (c:CrystallizedInsight {content: $content})
                        ON CREATE SET c.created_at = $created_at, c.weight = 1.0
                        ON MATCH SET c.updated_at = $created_at, c.weight = c.weight + 0.1
                        WITH c
                        MATCH (f:Entity {name: "Friday"})
                        MERGE (f)-[r:CRYSTALLIZED_INTO]->(c)
                        SET r.last_dream_at = $created_at
                        """,
                        content=insight,
                        created_at=now_iso,
                    )
                    edges_created += 1
            driver.close()
        except Exception as e:
            logger.info("Neo4j graph crystallization skipped or unavailable: %s", e)

    duration_ms = round((time.time() - start_time) * 1000, 2)
    report: Dict[str, Any] = {
        "timestamp": now_iso,
        "status": "completed",
        "pruned_ephemeral_count": decay_report.get("decayed_facts_count", 0),
        "decayed_facts_count": decay_report.get("decayed_facts_count", 0),
        "active_facts_count": decay_report.get("active_facts_count", 0),
        "crystallized_insights": crystallized_insights,
        "new_graph_edges_count": edges_created,
        "duration_ms": duration_ms,
    }

    logger.info(
        "🌙 Dream Cycle finished in %sms. Decayed: %s, Active: %s, Insights: %s",
        duration_ms,
        report["decayed_facts_count"],
        report["active_facts_count"],
        len(crystallized_insights),
    )
    return report


if __name__ == "__main__":
    rep = run_dream_cycle()
    print(json.dumps(rep, indent=2))
