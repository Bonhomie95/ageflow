from __future__ import annotations

from pathlib import Path
from typing import List
from unicodedata import name

from ..config.settings import settings
from ..utils.logger import get_logger
from ..utils.filesystem import read_json, write_json
from ..utils.slug import slugify

from .models import ImageCandidate, ImageManifest, VerifiedDate
from .downloader import download_file
from .exif import extract_exif_date

# Primary / backup sources
from .wikimedia import (
    search_commons_files,
    fetch_commons_images,
    extract_verified_date_from_commons,
)
from .wikipedia_page import fetch_wikipedia_page_images
from .imdb_images import fetch_imdb_images
from .bing_images import search_bing_images
from .serpapi_images import (
    serpapi_enabled,
    search_google_images_serpapi,
    to_candidate_items,
)

log = get_logger("images")


# ---------------------------------------------------------------------
# PATH HELPERS
# ---------------------------------------------------------------------


def manifest_path(celebrity_name: str) -> Path:
    return Path("data/images_manifests") / f"{slugify(celebrity_name)}.json"


def raw_dir(celebrity_name: str) -> Path:
    return Path("images/raw") / slugify(celebrity_name)


# ---------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------


def _safe_ext(url: str) -> str:
    u = url.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        if ext in u:
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def _year_from_date(date_str: str) -> int:
    return int(date_str[:4])


def _verify_with_commons(candidate: ImageCandidate) -> ImageCandidate:
    if candidate.source != "wikimedia":
        return candidate

    date_str = candidate.meta.get("commons_date")
    method = candidate.meta.get("commons_date_method")
    if date_str and method:
        candidate.verified = True
        candidate.verified_date = VerifiedDate(
            date=date_str,
            year=_year_from_date(date_str),
            method=str(method),
            confidence=0.95,
        )
    return candidate


def _verify_with_exif(candidate: ImageCandidate) -> ImageCandidate:
    if not candidate.local_path:
        return candidate

    d, tag = extract_exif_date(Path(candidate.local_path))
    if not d:
        return candidate

    candidate.verified = True
    candidate.verified_date = VerifiedDate(
        date=d,
        year=_year_from_date(d),
        method=f"exif:{tag}",
        confidence=0.98 if tag == "DateTimeOriginal" else 0.93,
    )
    return candidate


def _download_candidate(
    candidate: ImageCandidate, idx: int, celebrity_name: str
) -> ImageCandidate:
    outdir = raw_dir(celebrity_name)
    outdir.mkdir(parents=True, exist_ok=True)

    ext = _safe_ext(candidate.image_url)
    filename = f"{idx:03d}_{slugify(candidate.title)[:60]}{ext}"
    outpath = outdir / filename

    try:
        download_file(candidate.image_url, outpath)
        candidate.local_path = outpath.as_posix()
    except Exception as e:
        candidate.meta["download_error"] = str(e)

    return candidate


# ---------------------------------------------------------------------
# MAIN COLLECTOR
# ---------------------------------------------------------------------


def collect_images_for_celebrity(
    celebrity_name: str,
    target_year_end: int,
    force: bool = False,
) -> ImageManifest:
    """
    Production-grade image collector.

    Guarantees:
    - Multiple independent sources
    - Zero hard dependency on any API
    - Never crashes if a source fails
    - Enforces reaching 2024 / 2025 (verified)
    - Feeds morph-safe images downstream
    """

    settings.ensure_dirs()
    Path("data/images_manifests").mkdir(parents=True, exist_ok=True)
    raw_dir(celebrity_name).mkdir(parents=True, exist_ok=True)

    mp = manifest_path(celebrity_name)
    if mp.exists() and not force:
        cached = read_json(mp)
        return ImageManifest.model_validate(cached)

    candidates: List[ImageCandidate] = []

    # ==============================================================
    # SOURCE 1 — WIKIMEDIA COMMONS (DATED & FACTUAL)
    # ==============================================================

    log.info("🔍 Wikimedia Commons search…")
    try:
        titles = search_commons_files(celebrity_name, limit=30)
        commons_imgs = fetch_commons_images(titles)

        for ci in commons_imgs:
            date_str, method = extract_verified_date_from_commons(ci.extmeta)
            cand = ImageCandidate(
                source="wikimedia",
                title=ci.title,
                page_url=ci.page_url,
                image_url=ci.image_url,
                meta={
                    "commons_date": date_str,
                    "commons_date_method": method,
                },
            )
            candidates.append(_verify_with_commons(cand))
    except Exception as e:
        log.warning(f"⚠️ Wikimedia Commons failed: {e}")

    # ==============================================================
    # SOURCE 2 — WIKIPEDIA PAGE IMAGES (CLEAN PORTRAITS)
    # ==============================================================

    log.info("🧠 Wikipedia page images…")
    try:
        for it in fetch_wikipedia_page_images(celebrity_name, limit=10):
            candidates.append(
                ImageCandidate(
                    source="wikipedia_page",
                    title=it["title"],
                    page_url=it["page_url"],
                    image_url=it["image_url"],
                    meta={},
                )
            )
    except Exception as e:
        log.warning(f"⚠️ Wikipedia page images failed: {e}")

    # ==============================================================
    # SOURCE 3 — IMDb IMAGE STILLS (MORPH-FRIENDLY)
    # ==============================================================

    log.info("🎬 IMDb image stills…")
    try:
        for it in fetch_imdb_images(celebrity_name, limit=15):
            candidates.append(
                ImageCandidate(
                    source="imdb",
                    title=it["title"],
                    page_url=it["page_url"],
                    image_url=it["image_url"],
                    meta={},
                )
            )
    except Exception as e:
        log.warning(f"⚠️ IMDb images failed: {e}")

    # ==============================================================
    # SOURCE 4 — BING IMAGES (NO API KEY)
    # ==============================================================

    log.info("🔍 Bing Images fallback…")
    bing_queries = [
        f"{celebrity_name} face close up",
        f"{celebrity_name} interview headshot",
        f"{celebrity_name} movie still face",
    ]

    for q in bing_queries:
        try:
            for it in search_bing_images(q, limit=10):
                candidates.append(
                    ImageCandidate(
                        source="bing",
                        title=it["title"],
                        page_url=it["page_url"],
                        image_url=it["image_url"],
                        meta={},
                    )
                )
        except Exception as e:
            log.warning(f"⚠️ Bing query failed ({q}): {e}")

    # ==============================================================
    # SOURCE 5 — SERPAPI (OPTIONAL BONUS)
    # ==============================================================

    if serpapi_enabled():
        log.info("🔍 SerpAPI (optional)…")
        queries = [
            f"{ celebrity_name} Titanic interview portrait",
            f"{ celebrity_name} Romeo and Juliet 1996 face",
            f"{ celebrity_name} early career headshot",
            f"{ celebrity_name} 1990s portrait",
            f"{ celebrity_name} 2000s interview close up",
            f"{ celebrity_name} recent portrait 2024",
        ]

        for q in queries:
            raw = search_google_images_serpapi(q, limit=8)
            for it in to_candidate_items(raw):
                candidates.append(
                    ImageCandidate(
                        source="serpapi",
                        title=it["title"],
                        page_url=it.get("page_url"),
                        image_url=it["image_url"],
                        meta=it.get("meta") or {},
                    )
                )

    # ==============================================================
    # DOWNLOAD & EXIF VERIFICATION
    # ==============================================================

    downloaded: List[ImageCandidate] = []
    max_downloads = 100

    log.info(f"⬇️ Downloading up to {min(len(candidates), max_downloads)} images…")

    for idx, cand in enumerate(candidates[:max_downloads], start=1):
        cand = _download_candidate(cand, idx, celebrity_name)
        cand = _verify_with_exif(cand)
        downloaded.append(cand)

    # ==============================================================
    # BUILD MANIFEST
    # ==============================================================

    verified_years = sorted(
        {c.verified_date.year for c in downloaded if c.verified and c.verified_date}
    )
    verified_count = sum(1 for c in downloaded if c.verified)

    manifest = ImageManifest(
        celebrity_name=celebrity_name,
        celebrity_slug=slugify(celebrity_name),
        target_year_end=target_year_end,
        candidates=downloaded,
        verified_years=verified_years,
        verified_count=verified_count,
    )

    write_json(mp, manifest.model_dump())

    # ==============================================================
    # HARD REQUIREMENT — MUST REACH 2024 / 2025
    # ==============================================================

    must_year = target_year_end - 1
    if not any(y >= must_year for y in verified_years):
        raise RuntimeError(
            f"[HARD FAIL] No VERIFIED image for year ≥ {must_year}. "
            f"Verified years found: {verified_years}"
        )

    log.info(
        f"✅ Collected {len(downloaded)} images | "
        f"verified={verified_count} | "
        f"verified_years={verified_years}"
    )

    return manifest
