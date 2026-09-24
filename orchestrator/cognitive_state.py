"""Empathy & Cognitive State Tracking Engine.

Tracks user cognitive workload, urgency, stress level, and interaction mode,
dynamically calibrating agent persona, response brevity, and communication tone.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_STATE: Dict[str, Any] = {
    "current_mode": "tactical_sprint",
    "urgency_level": 0.5,
    "stress_level": 0.2,
    "valence": 0.8,
    "last_interaction_at": datetime.now(timezone.utc).isoformat(),
    "response_calibration": {
        "brevity": "high",
        "tone": "sharp_tactical",
        "humor_frequency": "balanced",
    },
    "recent_context_tags": ["architecture", "execution"],
    "summary": "Tactical execution mode with high brevity and sharp MCU-grade efficiency.",
}


def _resolve_state_path(path: Optional[str] = None) -> Path:
    if path:
        target = path
    elif os.getenv("COGNITIVE_STATE_PATH"):
        target = os.getenv("COGNITIVE_STATE_PATH")
    elif os.path.exists("/app"):
        target = "/app/core/cognitive_state.json"
    else:
        # Local development / test fallback
        target = os.path.join(os.path.dirname(__file__), "..", "core", "cognitive_state.json")

    p = Path(target)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return p


def get_cognitive_state(state_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve current cognitive and emotional state."""
    p = _resolve_state_path(state_path)
    if not p.exists():
        return dict(DEFAULT_STATE)

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_STATE)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_STATE)


def update_cognitive_state(
    updates: Dict[str, Any],
    state_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Update cognitive state fields and persist to disk."""
    current = get_cognitive_state(state_path)

    # Update top-level primitives
    for k in ("current_mode", "urgency_level", "stress_level", "valence", "summary"):
        if k in updates and updates[k] is not None:
            if k in ("urgency_level", "stress_level", "valence"):
                current[k] = round(float(updates[k]), 2)
            else:
                current[k] = str(updates[k])

    # Update nested response calibration
    if "response_calibration" in updates and isinstance(updates["response_calibration"], dict):
        if not isinstance(current.get("response_calibration"), dict):
            current["response_calibration"] = {}
        current["response_calibration"].update(updates["response_calibration"])

    # Update recent context tags
    if "recent_context_tags" in updates and isinstance(updates["recent_context_tags"], list):
        existing_tags = current.get("recent_context_tags", [])
        new_tags = [str(t).lower().strip() for t in updates["recent_context_tags"] if t]
        combined = list(dict.fromkeys(new_tags + existing_tags))[:10]
        current["recent_context_tags"] = combined

    current["last_interaction_at"] = datetime.now(timezone.utc).isoformat()

    # Recalculate summary if not explicitly provided
    if "summary" not in updates:
        mode = current.get("current_mode", "tactical_sprint")
        brevity = current.get("response_calibration", {}).get("brevity", "high")
        tone = current.get("response_calibration", {}).get("tone", "sharp_tactical")
        current["summary"] = (
            f"Mode: {mode} | Brevity: {brevity} | Tone: {tone} | Urgency: {current.get('urgency_level')}"
        )

    p = _resolve_state_path(state_path)
    try:
        p.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    return current


def detect_state_from_prompt(prompt: str) -> Dict[str, Any]:
    """Heuristic detector that derives urgency, emotional tone, and mode from prompt text."""
    p_lower = prompt.lower()
    inferred: Dict[str, Any] = {}

    urgent_signals = [
        "urgent",
        "jaldi",
        "asap",
        "quick",
        "emergency",
        "broken",
        "down",
        "error",
        "fail",
    ]
    arch_signals = [
        "architecture",
        "blueprint",
        "scale",
        "system design",
        "future",
        "schema",
        "database",
        "modular",
    ]
    casual_signals = ["kya lagta hai", "soch raha tha", "explore", "idea", "brainstorm", "opinion"]

    is_urgent = any(re.search(rf"\b{s}\b", p_lower) for s in urgent_signals)
    is_arch = any(re.search(rf"\b{s}\b", p_lower) for s in arch_signals)
    is_casual = any(s in p_lower for s in casual_signals)

    if is_urgent:
        inferred["current_mode"] = "tactical_sprint"
        inferred["urgency_level"] = 0.9
        inferred["stress_level"] = 0.7
        inferred["response_calibration"] = {
            "brevity": "high",
            "tone": "sharp_tactical",
            "humor_frequency": "minimal",
        }
    elif is_arch:
        inferred["current_mode"] = "deep_architecture"
        inferred["urgency_level"] = 0.4
        inferred["stress_level"] = 0.2
        inferred["response_calibration"] = {
            "brevity": "detailed",
            "tone": "structured_analytical",
            "humor_frequency": "balanced",
        }
    elif is_casual:
        inferred["current_mode"] = "casual_brainstorm"
        inferred["urgency_level"] = 0.2
        inferred["stress_level"] = 0.1
        inferred["response_calibration"] = {
            "brevity": "medium",
            "tone": "visionary_warm",
            "humor_frequency": "high",
        }

    return inferred


def format_state_prompt(state: Optional[Dict[str, Any]] = None) -> str:
    """Format cognitive state into a prompt-injectable directive string."""
    s = state or get_cognitive_state()
    cal = s.get("response_calibration", {})
    return (
        f"[Cognitive State: mode={s.get('current_mode')}, "
        f"urgency={s.get('urgency_level')}, "
        f"brevity={cal.get('brevity')}, "
        f"tone={cal.get('tone')}]"
    )
