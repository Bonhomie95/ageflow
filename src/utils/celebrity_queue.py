from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pathlib import Path

from ..config.settings import settings
from .filesystem import read_json, write_json


def load_queue() -> list[str]:
    q = read_json(settings.queue_file, default=[])
    if not isinstance(q, list):
        raise ValueError("queue.json must be a JSON array of strings.")
    return [str(x).strip() for x in q if str(x).strip()]


def load_used() -> dict:
    used = read_json(settings.used_file, default={})
    if not isinstance(used, dict):
        return {}
    return used


def get_next_celebrity() -> Optional[str]:
    queue = load_queue()
    used = load_used()
    for name in queue:
        if name not in used:
            return name
    return None


def mark_used(name: str, meta: dict) -> None:
    used = load_used()
    used[name] = {
        "processed_at": datetime.now(timezone.utc).isoformat(),
        **meta,
    }
    write_json(settings.used_file, used)
