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
from .wikimedia import (
    search_commons_files,
    fetch_commons_images,
    extract_verified_date_from_commons,
)
from .serpapi_images import (
    serpapi_enabled,
    search_google_images_serpapi,
    to_candidate_items,
)

log = get_logger("images")


def manifest_path(celebrity_name: str) -> Path:
    return Path("data/images_manifests") / f"{slugify(celebrity_name)}.json"


def raw_dir(celebrity_name: str) -> Path:
    return Path("images/raw") / slugify(celebrity_name)


def _safe_ext(url: str) -> str:
    u = url.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        if ext in u:
            return ext if ext != ".jpeg" else ".jpg"
    return ".jpg"


def _year_from_date(date_str: str) -> int:
    return int(date_str[:4])


def _verify_with_exif(candidate: ImageCandidate) -> ImageCandidate:
    """
    After download, try EXIF DateTimeOriginal, etc.
    If found -> verified = True.
    """
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


def _verify_with_commons_extmeta(candidate: ImageCandidate) -> ImageCandidate:
    """
    If Commons extmetadata contains a date, mark verified even before EXIF.
    """
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


def _download_candidate(
    candidate: ImageCandidate, idx: int, celeb: str
) -> ImageCandidate:
    outdir = raw_dir(celeb)
    outdir.mkdir(parents=True, exist_ok=True)
    ext = _safe_ext(candidate.image_url)
    outpath = outdir / f"{idx:03d}_{slugify(candidate.title)[:40]}{ext}"
    try:
        download_file(candidate.image_url, outpath)
        candidate.local_path = outpath.as_posix()
    except Exception as e:
        candidate.meta["download_error"] = str(e)
    return candidate


def collect_images_for_celebrity(
    celebrity_name: str,
    target_year_end: int,
    force: bool = False,
    commons_limit: int = 25,
    serpapi_limit: int = 25,
) -> ImageManifest:
    """
    Collect candidates and verify dates.
    HARD RULE: must include at least one VERIFIED image whose year is >= (target_year_end - 1)
              i.e., for 2025 target: must have verified 2024 or 2025.
    """
    settings.ensure_dirs()
    Path("data/images_manifests").mkdir(parents=True, exist_ok=True)
    raw_dir(celebrity_name).mkdir(parents=True, exist_ok=True)

    mp = manifest_path(celebrity_name)
    if mp.exists() and not force:
        cached = read_json(mp)
        return ImageManifest.model_validate(cached)

    candidates: List[ImageCandidate] = []

    # ---- Source 1: Wikimedia Commons (best free verification)
    commons_titles = search_commons_files(celebrity_name, limit=commons_limit)
    commons_imgs = fetch_commons_images(commons_titles)
    for ci in commons_imgs:
        date_str, method = extract_verified_date_from_commons(ci.extmeta)
        cand = ImageCandidate(
            source="wikimedia",
            title=ci.title,
            page_url=ci.page_url,
            image_url=ci.image_url,
            meta={
                "commons_extmeta": ci.extmeta,
                "commons_date": date_str,
                "commons_date_method": method,
            },
        )
        cand = _verify_with_commons_extmeta(cand)
        candidates.append(cand)

    # ---- Source 2: SerpAPI (optional) → verify via EXIF after download
    if serpapi_enabled():
        log.info("✅ SERPAPI enabled → using Google Images as backup source.")
        q = f"{celebrity_name} portrait photo {target_year_end}"
        raw = search_google_images_serpapi(q, limit=serpapi_limit)
        norm = to_candidate_items(raw)
        for it in norm:
            candidates.append(
                ImageCandidate(
                    source="serpapi",
                    title=it["title"],
                    page_url=it.get("page_url"),
                    image_url=it["image_url"],
                    meta=it.get("meta") or {},
                )
            )
    else:
        log.warning("SERPAPI_KEY not set → skipping serpapi source (Wikimedia only).")

    # ---- Download a capped set (avoid huge bandwidth); verify EXIF after download
    downloaded: List[ImageCandidate] = []
    for idx, c in enumerate(candidates[:60], start=1):
        c = _download_candidate(c, idx, celebrity_name)
        c = _verify_with_exif(c)
        downloaded.append(c)

    # ---- Build manifest
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

    # ---- Enforce “must reach 2024-2025 minimum”
    must_year = target_year_end - 1  # for 2025 -> must have 2024 or 2025
    ok_recent = any(y >= must_year for y in verified_years)
    if not ok_recent:
        raise RuntimeError(
            f"[HARD FAIL] No VERIFIED image found for year >= {must_year} "
            f"(needs {must_year} or {target_year_end}). "
            f"Verified years found: {verified_years}. "
            f"Tip: set SERPAPI_KEY for more coverage, or add more sources next."
        )

    log.info(
        f"✅ Collected {len(downloaded)} candidates | verified={verified_count} | verified_years={verified_years}"
    )
    return manifest
