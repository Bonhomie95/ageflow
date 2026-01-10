from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class VerifiedDate(BaseModel):
    date: str  # YYYY-MM-DD
    year: int
    method: str  # exif:DateTimeOriginal | commons:DateTimeOriginal | commons:DateTime | none
    confidence: float


class ImageCandidate(BaseModel):
    source: str  # wikimedia | serpapi
    title: str
    page_url: Optional[str] = None
    image_url: str

    # Downloaded file path (filled after download)
    local_path: Optional[str] = None

    # Date verification info
    verified: bool = False
    verified_date: Optional[VerifiedDate] = None

    # Extra metadata (license, author, etc.)
    meta: Dict[str, Any] = Field(default_factory=dict)


class ImageManifest(BaseModel):
    celebrity_name: str
    celebrity_slug: str
    target_year_end: int

    # We keep all candidates (verified + unverified)
    candidates: list[ImageCandidate] = Field(default_factory=list)

    # Convenience indexes
    verified_years: list[int] = Field(default_factory=list)
    verified_count: int = 0
