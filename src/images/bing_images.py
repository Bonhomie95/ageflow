from __future__ import annotations

import requests
import re
from typing import List, Dict


def search_bing_images(query: str, limit: int = 10) -> List[Dict]:
    """
    Lightweight Bing Images scraper (no API key).
    """
    url = f"https://www.bing.com/images/search?q={query.replace(' ', '+')}&form=HDRSC2"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    r.raise_for_status()

    results = []
    matches = re.findall(r'"murl":"(.*?)"', r.text)

    for m in matches[:limit]:
        results.append(
            {
                "title": "bing_image",
                "image_url": m,
                "page_url": url,
            }
        )

    return results
