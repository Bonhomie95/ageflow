from __future__ import annotations

from typing import Any, Dict, List

import requests

from ..config.settings import settings


def serpapi_enabled() -> bool:
    return bool(settings.serpapi_key)


def search_google_images_serpapi(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Google Images via SerpAPI.
    Requires SERPAPI_KEY.
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
    r = requests.get(
        "https://serpapi.com/search.json",
        params=params,
        headers=headers,
        timeout=settings.http_timeout,
    )
    r.raise_for_status()

    j = r.json()
    return j.get("images_results", []) or []


def to_candidate_items(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for it in raw:
        img = it.get("original") or it.get("thumbnail")
        link = it.get("link")
        title = it.get("title") or "serpapi_image"
        if img and isinstance(img, str):
            out.append(
                {
                    "title": title,
                    "image_url": img,
                    "page_url": link if isinstance(link, str) else None,
                    "meta": {
                        "source": it.get("source"),
                        "snippet": it.get("snippet"),
                        "position": it.get("position"),
                    },
                }
            )
    return out
