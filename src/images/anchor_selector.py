from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from ..utils.slug import slugify
from ..utils.filesystem import write_json
from .models import ImageCandidate, ImageManifest


# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

MAX_ANCHORS = 8
MIN_ANCHORS = 5
MIN_YEAR_GAP = 3  # minimum spacing between anchors (years)


# ---------------------------------------------------------------------
# DATA MODEL
# ---------------------------------------------------------------------


@dataclass
class Anchor:
    year: int
    age: int
    image_path: str
    source: str
    verified: bool


# ---------------------------------------------------------------------
# CORE LOGIC
# ---------------------------------------------------------------------


def select_anchors(
    manifest: ImageManifest,
    birth_year: int,
) -> List[Anchor]:
    """
    Select timeline anchors from collected images.

    Strategy:
    1. Prefer VERIFIED images
    2. Sort chronologically
    3. Enforce year spacing
    4. Cap to MAX_ANCHORS
    """

    # Step 1 — keep only images with known year and local file
    dated: List[ImageCandidate] = []
    for c in manifest.candidates:
        if not c.verified:
            continue
        if c.verified_date is None:
            continue
        if c.local_path is None:
            continue
        dated.append(c)

    if not dated:
        raise RuntimeError("No verified images available for anchor selection")

    # Step 2 — sort by year (safe: verified_date is guaranteed)
    dated.sort(key=lambda c: c.verified_date.year)  # type: ignore[arg-type]

    anchors: List[Anchor] = []
    last_year: int | None = None

    for c in dated:
        vd = c.verified_date
        lp = c.local_path

        # Explicit narrowing for type checker
        assert vd is not None
        assert lp is not None

        year = vd.year

        if last_year is not None and (year - last_year) < MIN_YEAR_GAP:
            continue

        age = year - birth_year

        anchors.append(
            Anchor(
                year=year,
                age=age,
                image_path=lp,
                source=c.source,
                verified=True,
            )
        )

        last_year = year

        if len(anchors) >= MAX_ANCHORS:
            break

    # Step 3 — fallback if spacing was too strict
    if len(anchors) < MIN_ANCHORS:
        anchors = _relaxed_selection(dated, birth_year)

    return anchors


def _relaxed_selection(
    candidates: List[ImageCandidate],
    birth_year: int,
) -> List[Anchor]:
    """
    Fallback selection if strict spacing fails.
    Picks evenly across the timeline.
    """

    valid = []
    for c in candidates:
        if c.verified_date is None or c.local_path is None:
            continue
        valid.append(c)

    years = sorted({c.verified_date.year for c in valid})  # type: ignore[arg-type]

    if len(years) < 2:
        raise RuntimeError("Not enough distinct years for anchor selection")

    span = years[-1] - years[0]
    step = max(1, span // MAX_ANCHORS)

    anchors: List[Anchor] = []
    used_years: set[int] = set()

    for c in valid:
        vd = c.verified_date
        lp = c.local_path

        assert vd is not None
        assert lp is not None

        y = vd.year

        if any(abs(y - uy) < step for uy in used_years):
            continue

        anchors.append(
            Anchor(
                year=y,
                age=y - birth_year,
                image_path=lp,
                source=c.source,
                verified=True,
            )
        )

        used_years.add(y)

        if len(anchors) >= MAX_ANCHORS:
            break

    return anchors


# ---------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------


def save_anchor_timeline(
    celebrity_name: str,
    anchors: List[Anchor],
) -> Path:
    """
    Save anchor timeline JSON for downstream morphing / video.
    """

    out_dir = Path("data/anchors")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{slugify(celebrity_name)}.json"

    payload = {
        "celebrity": celebrity_name,
        "anchors": [
            {
                "year": a.year,
                "age": a.age,
                "image_path": a.image_path,
                "source": a.source,
                "verified": a.verified,
            }
            for a in anchors
        ],
    }

    write_json(out_path, payload)
    return out_path
