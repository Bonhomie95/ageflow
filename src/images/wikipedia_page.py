from __future__ import annotations

import requests
from typing import List, Dict

WIKI_API = "https://en.wikipedia.org/w/api.php"


def fetch_wikipedia_page_images(name: str, limit: int = 10) -> List[Dict]:
    """
    Fetch images directly embedded on a celebrity's Wikipedia page.
    These are usually clean portraits.
    """
    params = {
        "action": "query",
        "format": "json",
        "prop": "images",
        "titles": name,
    }

    r = requests.get(WIKI_API, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    pages = data.get("query", {}).get("pages", {})
    images = []

    for page in pages.values():
        for img in page.get("images", []):
            title = img.get("title", "")
            if any(
                x in title.lower() for x in ["portrait", "photo", "headshot", "face"]
            ):
                images.append(
                    {
                        "title": title,
                        "image_url": f"https://commons.wikimedia.org/wiki/Special:FilePath/{title.replace('File:', '')}",
                        "page_url": f"https://en.wikipedia.org/wiki/{name.replace(' ', '_')}",
                    }
                )
            if len(images) >= limit:
                break

    return images
