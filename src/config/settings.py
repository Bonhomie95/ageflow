from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    base_dir: Path = Path(".")
    data_dir: Path = Path("data")
    facts_dir: Path = Path("data/facts")
    cache_dir: Path = Path("data/cache")
    celebrities_dir: Path = Path("data/celebrities")

    queue_file: Path = Path("data/celebrities/queue.json")
    used_file: Path = Path("data/cache/used_names.json")

    # Runtime
    target_year_end: int = int(os.getenv("TARGET_YEAR_END", "2025"))
    http_timeout: int = int(os.getenv("HTTP_TIMEOUT", "20"))
    user_agent: str = os.getenv("USER_AGENT", "ageflow/1.0")

    # APIs
    serpapi_key: str | None = os.getenv("SERPAPI_KEY")

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.facts_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.celebrities_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
