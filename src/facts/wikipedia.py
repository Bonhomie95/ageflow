from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

import requests

from ..config.settings import settings


@dataclass
class WikipediaResolved:
    title: str
    pageid: int
    url: str
    description: Optional[str]
    extract: Optional[str]
    wikidata_id: Optional[str]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": settings.user_agent})
    return s


def search_best_title(name: str) -> Optional[str]:
    """
    Uses MediaWiki opensearch to get best matching title.
    """
    s = _session()
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "opensearch",
        "search": name,
        "limit": 5,
        "namespace": 0,
        "format": "json",
    }
    r = s.get(url, params=params, timeout=settings.http_timeout)
    r.raise_for_status()
    data = r.json()
    titles = data[1] if isinstance(data, list) and len(data) > 1 else []
    return titles[0] if titles else None


def resolve_page(title: str) -> WikipediaResolved:
    """
    Fetch pageid + canonical url + wikidata Q-id via pageprops.
    """
    s = _session()
    api = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "info|pageprops|extracts",
        "inprop": "url",
        "ppprop": "wikibase_item",
        "exintro": 1,
        "explaintext": 1,
        "redirects": 1,
        "titles": title,
    }
    r = s.get(api, params=params, timeout=settings.http_timeout)
    r.raise_for_status()
    j = r.json()

    pages: Dict[str, Any] = j.get("query", {}).get("pages", {})
    if not pages:
        raise ValueError(f"Wikipedia page not found for title: {title}")

    page = next(iter(pages.values()))
    if "missing" in page:
        raise ValueError(f"Wikipedia page missing: {title}")

    pageid = int(page.get("pageid"))
    canonical_title = page.get("title", title)
    fullurl = (
        page.get("fullurl")
        or f"https://en.wikipedia.org/wiki/{canonical_title.replace(' ', '_')}"
    )
    extract = page.get("extract")
    wikidata_id = (page.get("pageprops") or {}).get("wikibase_item")

    # Description is available via REST summary endpoint; optional.
    description = None
    try:
        rest = f"https://en.wikipedia.org/api/rest_v1/page/summary/{canonical_title.replace(' ', '%20')}"
        rr = s.get(rest, timeout=settings.http_timeout)
        if rr.ok:
            description = (rr.json() or {}).get("description")
    except Exception:
        pass

    return WikipediaResolved(
        title=canonical_title,
        pageid=pageid,
        url=fullurl,
        description=description,
        extract=extract,
        wikidata_id=wikidata_id,
    )
