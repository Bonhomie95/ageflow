from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceFlags(BaseModel):
    wikipedia: bool = False
    wikidata: bool = False


class TimelineItem(BaseModel):
    year: int
    label: str
    type: str = "unknown"
    confidence: float = 0.5
    source: str = "unknown"


class CelebrityFacts(BaseModel):
    name: str
    slug: str
    wikipedia_title: str
    wikipedia_url: str
    wikidata_id: str

    birth_date: str  # ISO YYYY-MM-DD
    confidence: float = 0.9

    target_year_end: int = 2025
    sources: SourceFlags = Field(default_factory=SourceFlags)
    timeline: List[TimelineItem] = Field(default_factory=list)

    raw: Dict[str, Any] = Field(default_factory=dict)
