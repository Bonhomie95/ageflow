from __future__ import annotations

from typing import Any, Dict, List

import requests

from ..config.settings import settings
from ..utils.logger import get_logger

log = get_logger("serpapi")


def serpapi_enabled() -> bool:
    return bool(settings.serpapi_key)


def search_google_images_serpapi(
    query: str, limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Google Images search via SerpAPI.

    HARD RULE:
    - NEVER crash the pipeline
    - On 401 / quota / network issues → return []
    """

    if not settings.serpapi_key:
        return []

    params = {
        "engine": "google_images",
        "q": query,
        "api_key": settings.serpapi_key,
        "num": min(limit, 100),
    }

    headers = {"User-Agent": settings.user_agent}

    try:
        r = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            headers=headers,
            timeout=settings.http_timeout,
        )

        if r.status_code == 401:
            log.error(
                "❌ SerpAPI unauthorized (401). "
                "Key invalid, quota exhausted, or Google Images disabled."
            )
            return []

        if r.status_code != 200:
            log.warning(
                f"⚠️ SerpAPI returned {r.status_code}. Skipping query: {query}"
            )
            return []

        data = r.json()
        return data.get("images_results", []) or []

    except Exception as e:
        log.warning(f"⚠️ SerpAPI request failed: {e}")
        return []


def to_candidate_items(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize SerpAPI image results.
    """
    out: List[Dict[str, Any]] = []

    for it in raw:
        img = it.get("original") or it.get("thumbnail")
        if not img:
            continue

        out.append(
            {
                "title": it.get("title") or "serpapi_image",
                "image_url": img,
                "page_url": it.get("link"),
                "meta": {
                    "source": it.get("source"),
                    "position": it.get("position"),
                    "snippet": it.get("snippet"),
                },
            }
        )

    return out
