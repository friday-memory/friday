"""
Friday — Autonomous Graph Wiring Engine

Every memory you store automatically becomes nodes and edges
in your Neo4j knowledge graph. No manual linking needed.

Uses DeepSeek Flash to extract entities and relationships,
then upserts them into Neo4j as :Entity nodes with typed edges.
"""

import json
import logging
from typing import Optional

logger = logging.getLogger("friday.auto_graph")


async def auto_extract_and_link_graph(
    text: str,
    project: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
):
    """
    Extract entities + relationships from text via LLM,
    then upsert them into the Neo4j knowledge graph.
    """
    try:
        entities = await _extract_entities(text, project, api_key, base_url, model)
        if entities:
            await _upsert_to_neo4j(entities, project, neo4j_uri, neo4j_user, neo4j_password)
            logger.info(f"[auto_graph] {project}: {len(entities.get('entities', []))} nodes, {len(entities.get('links', []))} edges upserted.")
    except Exception as e:
        logger.warning(f"[auto_graph] Non-fatal error: {e}")


async def _extract_entities(text: str, project: str, api_key: str, base_url: str, model: str) -> Optional[dict]:
    """Call LLM to extract structured entities and relationships."""
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        system_prompt = """You are a knowledge graph extraction engine.
Extract entities and relationships from the given text.
Return ONLY valid JSON in this exact format:
{
  "entities": ["EntityName1", "EntityName2"],
  "links": [{"from": "EntityName1", "to": "EntityName2", "label": "USES"}]
}
Rules:
- Entity names: PascalCase, max 4 words, no special characters
- Labels: UPPER_SNAKE_CASE (e.g. USES, INTEGRATES, MANAGES, DEPENDS_ON)
- Max 10 entities, max 15 links
- Only include meaningful domain concepts, not generic words
- If nothing meaningful found, return {"entities": [], "links": []}"""

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Project: {project}\n\nText: {text[:3000]}"},
            ],
            max_tokens=600,
            temperature=0.1,
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown code blocks if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        logger.debug(f"[auto_graph] LLM extraction failed: {e}")
        return None


async def _upsert_to_neo4j(entities: dict, project: str, uri: str, user: str, password: str):
    """Upsert extracted entities and edges into Neo4j."""
    try:
        from neo4j import AsyncGraphDatabase

        async with AsyncGraphDatabase.driver(uri, auth=(user, password)) as driver:
            async with driver.session() as session:
                # Upsert project node
                await session.run(
                    "MERGE (p:Entity {name: $name}) SET p.type = 'Project', p.project = $project",
                    name=project, project=project
                )

                # Upsert entity nodes
                for entity_name in entities.get("entities", []):
                    if entity_name and len(entity_name) > 1:
                        await session.run(
                            "MERGE (n:Entity {name: $name}) "
                            "ON CREATE SET n.project = $project, n.created_at = datetime() "
                            "ON MATCH SET n.last_seen = datetime()",
                            name=entity_name, project=project
                        )
                        # Link entity to project
                        await session.run(
                            "MATCH (p:Entity {name: $proj}), (n:Entity {name: $name}) "
                            "MERGE (p)-[:CONTAINS]->(n)",
                            proj=project, name=entity_name
                        )

                # Upsert relationship edges
                for link in entities.get("links", []):
                    src = link.get("from", "")
                    tgt = link.get("to", "")
                    label = link.get("label", "RELATES_TO").upper().replace(" ", "_")
                    if src and tgt and src != tgt:
                        await session.run(
                            f"MATCH (a:Entity {{name: $src}}), (b:Entity {{name: $tgt}}) "
                            f"MERGE (a)-[:{label}]->(b)",
                            src=src, tgt=tgt
                        )
    except Exception as e:
        logger.warning(f"[auto_graph] Neo4j upsert failed: {e}")
