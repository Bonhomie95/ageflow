from __future__ import annotations

from src.config.settings import settings
from src.utils.celebrity_queue import load_queue
from src.facts.resolver import resolve_celebrity_facts

if __name__ == "__main__":
    settings.ensure_dirs()
    for name in load_queue():
        resolve_celebrity_facts(name, force=False)
