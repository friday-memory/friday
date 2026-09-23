"""
Friday — Query Router

Routes incoming queries to the best memory layer
based on query type, recency, and relevance scoring.
"""

import logging

logger = logging.getLogger("friday.router")


async def route_query(query: str, layers: list) -> dict:
    """Route query to best available layer and merge results."""
    results = []
    for layer in layers:
        try:
            layer_results = await layer.search(query)
            results.extend(layer_results)
        except Exception as e:
            logger.warning(f"Layer {layer.__class__.__name__} failed: {e}")

    # Deduplicate and rank by relevance score
    seen = set()
    unique = []
    for r in sorted(results, key=lambda x: x.get("score", 0), reverse=True):
        key = r.get("content", "")[:100]
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return {"results": unique[:10]}
