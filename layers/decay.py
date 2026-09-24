"""Dynamic Memory Heat & Decay Engine.

Implements biologically-inspired synaptic decay and recall-based potentiation
for persistent memories and facts.
"""

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def calculate_decayed_energy(
    initial_energy: float,
    last_recalled_at: Optional[str] = None,
    created_at: Optional[str] = None,
    half_life_days: float = 14.0,
    current_time: Optional[datetime] = None,
) -> float:
    """Calculate the decayed energy score using exponential half-life decay.

    Formula: E(t) = E_0 * (0.5 ** (delta_days / half_life_days))
    Clamped to range [0.05, 2.0].
    """
    if half_life_days <= 0:
        return max(0.05, min(2.0, initial_energy))

    now = current_time or datetime.now(timezone.utc)
    ref_str = last_recalled_at or created_at

    if not ref_str:
        return max(0.05, min(2.0, initial_energy))

    try:
        clean_str = ref_str.replace("Z", "+00:00")
        if "T" not in clean_str and " " in clean_str:
            clean_str = clean_str.replace(" ", "T")
        if "+" not in clean_str and "-" not in clean_str[10:]:
            clean_str += "+00:00"
        ref_dt = datetime.fromisoformat(clean_str)
    except Exception:
        return max(0.05, min(2.0, initial_energy))

    delta_seconds = (now - ref_dt).total_seconds()
    if delta_seconds < 0:
        delta_seconds = 0.0

    delta_days = delta_seconds / 86400.0
    decay_factor = math.pow(0.5, delta_days / half_life_days)
    new_energy = initial_energy * decay_factor

    return round(max(0.05, min(2.0, new_energy)), 4)


def record_memory_recall(
    fact_id: str,
    facts_path: Optional[str] = None,
    boost: float = 0.25,
    max_energy: float = 2.0,
) -> Optional[Dict[str, Any]]:
    """Boost energy score and record interaction timestamp upon memory recall."""
    path = Path(facts_path or os.getenv("FACTS_PATH", "/app/facts/facts.json"))
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    updated_fact = None
    now_iso = datetime.now(timezone.utc).isoformat()

    for f in data.get("facts", []):
        if f.get("id") == fact_id:
            current_energy = f.get("energy_score", 1.0)
            f["energy_score"] = round(min(max_energy, current_energy + boost), 4)
            f["recall_count"] = f.get("recall_count", 0) + 1
            f["last_recalled_at"] = now_iso
            if f.get("status") == "decayed":
                f["status"] = "active"
            updated_fact = dict(f)
            break

    if updated_fact:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return updated_fact


def apply_system_decay(
    facts_path: Optional[str] = None,
    half_life_days: float = 14.0,
    archive_threshold: float = 0.25,
) -> Dict[str, Any]:
    """Iterate through all facts and apply synaptic decay.

    Facts with energy_score < archive_threshold and not marked decay_immune
    are transitioned to status='decayed'.
    """
    path = Path(facts_path or os.getenv("FACTS_PATH", "/app/facts/facts.json"))
    if not path.exists():
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "evaluated_facts_count": 0,
            "decayed_facts_count": 0,
            "active_facts_count": 0,
            "half_life_days": half_life_days,
        }

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "evaluated_facts_count": 0,
            "decayed_facts_count": 0,
            "active_facts_count": 0,
            "half_life_days": half_life_days,
        }

    facts = data.get("facts", [])
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    decayed_count = 0
    active_count = 0

    for f in facts:
        if f.get("decay_immune", False):
            f["energy_score"] = 2.0
            if f.get("status") != "superseded":
                f["status"] = "active"
                active_count += 1
            continue

        if f.get("status") in ("superseded", "archived"):
            continue

        initial_energy = f.get("energy_score", 1.0)
        recalled_at = f.get("last_recalled_at")
        created_at = f.get("created_at")

        new_energy = calculate_decayed_energy(
            initial_energy=initial_energy,
            last_recalled_at=recalled_at,
            created_at=created_at,
            half_life_days=half_life_days,
            current_time=now,
        )
        f["energy_score"] = new_energy

        if new_energy < archive_threshold:
            f["status"] = "decayed"
            f["decayed_at"] = now_iso
            decayed_count += 1
        else:
            if f.get("status") != "superseded":
                f["status"] = "active"
                active_count += 1

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "timestamp": now_iso,
        "evaluated_facts_count": len(facts),
        "decayed_facts_count": decayed_count,
        "active_facts_count": active_count,
        "half_life_days": half_life_days,
    }
