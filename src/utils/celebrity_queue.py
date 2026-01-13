from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from pathlib import Path

from ..config.settings import settings
from .filesystem import read_json, write_json


# ---------------------------------------------------------------------
# INTERNAL LOADERS
# ---------------------------------------------------------------------

def load_queue() -> List[str]:
    """
    Load celebrity queue.
    Must be a JSON array of strings.
    """
    data = read_json(settings.queue_file, default=[])
    if not isinstance(data, list):
        raise ValueError("queue.json must be a JSON array of strings")

    return [str(x).strip() for x in data if str(x).strip()]


def load_used() -> Dict[str, dict]:
    """
    Load processed celebrities map.
    Format:
    {
        "Leonardo DiCaprio": {
            "processed_at": "...",
            "step": "anchors"
        }
    }
    """
    data = read_json(settings.used_file, default={})
    if not isinstance(data, dict):
        return {}
    return data


# ---------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------

def get_next_celebrity() -> Optional[str]:
    """
    Return the next unprocessed celebrity from the queue.
    """
    queue = load_queue()
    used = load_used()

    for name in queue:
        if name not in used:
            return name

    return None


def mark_used(name: str, *, step: str = "completed") -> None:
    """
    Mark a celebrity as processed.

    Args:
        name: Celebrity name
        step: Pipeline step completed (facts, images, anchors, video, etc.)
    """
    used = load_used()

    used[name] = {
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "step": step,
    }

    write_json(settings.used_file, used)
