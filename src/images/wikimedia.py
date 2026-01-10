from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests

from ..config.settings import settings


@dataclass
class CommonsImage:
    title: str
    page_url: str
    image_url: str
    extmeta: Dict[str, Any]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": settings.user_agent})
    return s


def _commons_api(params: Dict[str, Any]) -> Dict[str, Any]:
    s = _session()
    url = "https://commons.wikimedia.org/w/api.php"
    r = s.get(url, params=params, timeout=settings.http_timeout)
    r.raise_for_status()
    return r.json()


def _extract_extmeta_date(
    extmeta: Dict[str, Any],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Try to pull a real capture date from Commons extmetadata.
    Common keys: DateTimeOriginal, DateTime, DateTimeDigitized (varies).
    Return (YYYY-MM-DD, method_label)
    """
    if not extmeta:
        return None, None

    for key in ("DateTimeOriginal", "DateTimeDigitized", "DateTime", "Date"):
        node = extmeta.get(key)
        if not node:
            continue
        val = node.get("value") if isinstance(node, dict) else None
        if not val or not isinstance(val, str):
            continue
        # Often value contains time or templates; we take first ISO-like date if present.
        # Most reliable if it begins with YYYY-MM-DD or YYYY:MM:DD.
        v = val.strip()

        # Normalize formats
        # Examples: "2019-05-17 13:44:02", "2019:05:17 13:44:02", "2019-05-17"
        for sep in ("T", " "):
            if sep in v:
                v = v.split(sep)[0].strip()

        if len(v) >= 10:
            # Convert YYYY:MM:DD -> YYYY-MM-DD
            if v[4] == ":" and v[7] == ":":
                v = v[:10].replace(":", "-")
            if v[4] == "-" and v[7] == "-":
                return v[:10], f"commons:{key}"

    return None, None


def search_commons_files(query: str, limit: int = 20) -> List[str]:
    """
    Search Commons for file titles relevant to query.
    Returns a list of page titles like: "File:Something.jpg"
    """
    j = _commons_api(
        {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": f"{query} filetype:bitmap",
            "srlimit": limit,
            "srnamespace": 6,  # File namespace
        }
    )
    results = j.get("query", {}).get("search", []) or []
    titles = []
    for item in results:
        t = item.get("title")
        if t and isinstance(t, str) and t.startswith("File:"):
            titles.append(t)
    return titles


def fetch_commons_images(file_titles: List[str]) -> List[CommonsImage]:
    """
    Given file titles, fetch direct image URL + extmetadata.
    """
    if not file_titles:
        return []

    titles = "|".join(file_titles[:50])
    j = _commons_api(
        {
            "action": "query",
            "format": "json",
            "prop": "imageinfo|info",
            "titles": titles,
            "iiprop": "url|extmetadata",
            "inprop": "url",
            "redirects": 1,
        }
    )

    pages = j.get("query", {}).get("pages", {}) or {}
    out: List[CommonsImage] = []

    for _, p in pages.items():
        title = p.get("title")
        fullurl = p.get("fullurl")
        iis = p.get("imageinfo") or []
        if not title or not fullurl or not iis:
            continue
        ii = iis[0]
        image_url = ii.get("url")
        extmeta = ii.get("extmetadata") or {}
        if image_url:
            out.append(
                CommonsImage(
                    title=title, page_url=fullurl, image_url=image_url, extmeta=extmeta
                )
            )

    return out


def extract_verified_date_from_commons(
    extmeta: Dict[str, Any],
) -> Tuple[Optional[str], Optional[str]]:
    return _extract_extmeta_date(extmeta)
