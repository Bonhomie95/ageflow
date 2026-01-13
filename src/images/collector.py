from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..config.settings import settings
from ..utils.logger import get_logger
from ..utils.filesystem import read_json, write_json
from ..utils.slug import slugify

from .models import ImageCandidate, ImageManifest, VerifiedDate
from .downloader import download_file
from .exif import extract_exif_date

# Image sources
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


def build_portrait_query(name: str, year: int) -> str:
    """
    Generic, celebrity-agnostic, face-centric query.
    """
    return f"{name} portrait image facing camera directly {year}"


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
    if candidate.local_path is None:
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
    birth_year: int,
    target_year_end: int,
    force: bool = False,
) -> ImageManifest:
    """
    Year-aware, production-grade image collector.

    Notes:
    - Verified years come mostly from Wikimedia date metadata and EXIF.
    - Bing/IMDb/Wikipedia images typically lack reliable dating; they still help
      with face stock, but won't appear in verified_years unless EXIF exists.

    Strategy:
    - Start from birth_year + 10
    - Pull Wikimedia broad + Wikimedia year-aware
    - Add Wikipedia page portraits + IMDb stills
    - Add Bing year-aware portrait searches
    - Add SerpAPI year-aware searches if enabled
    """

    settings.ensure_dirs()
    Path("data/images_manifests").mkdir(parents=True, exist_ok=True)
    raw_dir(celebrity_name).mkdir(parents=True, exist_ok=True)

    mp = manifest_path(celebrity_name)
    if mp.exists() and not force:
        cached = read_json(mp)
        return ImageManifest.model_validate(cached)

    candidates: List[ImageCandidate] = []

    current_year = target_year_end
    start_year = birth_year + 10  # practical minimum

    log.info(
        f"📅 Year-aware search: {celebrity_name} from {start_year} → {current_year}"
    )

    # Dedup trackers
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    def push_candidate(cand: ImageCandidate) -> None:
        if cand.image_url in seen_urls:
            return
        if cand.title in seen_titles:
            return
        seen_urls.add(cand.image_url)
        seen_titles.add(cand.title)
        candidates.append(cand)

    # ==============================================================
    # SOURCE 1 — WIKIMEDIA COMMONS (BROAD + YEAR-AWARE)
    # ==============================================================

    log.info("🔍 Wikimedia Commons (broad + year-aware)…")
    try:
        # A) Broad
        titles = search_commons_files(celebrity_name, limit=40)
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
            push_candidate(_verify_with_commons(cand))

        # B) Year-aware (targeted)
        year_step = 2
        per_year_limit = 8

        for year in range(start_year, current_year + 1, year_step):
            q = f"{celebrity_name} {year}"
            year_titles = search_commons_files(q, limit=per_year_limit)
            if not year_titles:
                continue

            year_imgs = fetch_commons_images(year_titles)
            for ci in year_imgs:
                date_str, method = extract_verified_date_from_commons(ci.extmeta)
                cand = ImageCandidate(
                    source="wikimedia",
                    title=ci.title,
                    page_url=ci.page_url,
                    image_url=ci.image_url,
                    meta={
                        "commons_date": date_str,
                        "commons_date_method": method,
                        "query_year": year,
                    },
                )
                push_candidate(_verify_with_commons(cand))

    except Exception as e:
        log.warning(f"⚠️ Wikimedia Commons failed: {e}")

    # ==============================================================
    # SOURCE 2 — WIKIPEDIA PAGE IMAGES
    # ==============================================================

    log.info("🧠 Wikipedia page images…")
    try:
        for it in fetch_wikipedia_page_images(celebrity_name, limit=10):
            push_candidate(
                ImageCandidate(
                    source="wikipedia_page",
                    title=str(it.get("title") or f"{celebrity_name} wikipedia"),
                    page_url=str(it.get("page_url") or ""),
                    image_url=str(it.get("image_url") or ""),
                    meta={},
                )
            )
    except Exception as e:
        log.warning(f"⚠️ Wikipedia page images failed: {e}")

    # ==============================================================
    # SOURCE 3 — IMDb IMAGE STILLS
    # ==============================================================

    log.info("🎬 IMDb image stills…")
    try:
        for it in fetch_imdb_images(celebrity_name, limit=20):
            push_candidate(
                ImageCandidate(
                    source="imdb",
                    title=str(it.get("title") or f"{celebrity_name} imdb"),
                    page_url=str(it.get("page_url") or ""),
                    image_url=str(it.get("image_url") or ""),
                    meta={},
                )
            )
    except Exception as e:
        log.warning(f"⚠️ IMDb images failed: {e}")

    # ==============================================================
    # SOURCE 4 — BING YEAR-AWARE (PORTRAIT QUERIES)
    # ==============================================================

    log.info("🔍 Bing Images (year-aware)…")
    for year in range(start_year, current_year + 1):
        q = build_portrait_query(celebrity_name, year)
        try:
            results = search_bing_images(q, limit=5)
            if not results:
                continue
            for it in results:
                push_candidate(
                    ImageCandidate(
                        source="bing",
                        title=f"{celebrity_name} portrait {year}",
                        page_url=it["page_url"],
                        image_url=it["image_url"],
                        meta={"query_year": year},
                    )
                )
        except Exception as e:
            log.warning(f"⚠️ Bing failed for year {year}: {e}")

    # ==============================================================
    # SOURCE 5 — SERPAPI (OPTIONAL)
    # ==============================================================

    if serpapi_enabled():
        log.info("🔍 SerpAPI (year-aware)…")
        for year in range(start_year, current_year + 1, 3):
            q = build_portrait_query(celebrity_name, year)
            try:
                raw = search_google_images_serpapi(q, limit=3)
                for it in to_candidate_items(raw):
                    push_candidate(
                        ImageCandidate(
                            source="serpapi",
                            title=f"{celebrity_name} portrait {year}",
                            page_url=it.get("page_url"),
                            image_url=it["image_url"],
                            meta={"query_year": year},
                        )
                    )
            except Exception as e:
                log.warning(f"⚠️ SerpAPI failed for year {year}: {e}")

    # ==============================================================
    # DOWNLOAD & EXIF VERIFICATION
    # ==============================================================

    downloaded: List[ImageCandidate] = []
    max_downloads = 140

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

    log.info(
        f"✅ Collected {len(downloaded)} images | "
        f"verified={verified_count} | "
        f"verified_years={verified_years}"
    )

    return manifest
