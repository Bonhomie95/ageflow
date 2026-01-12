from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from typing import List, Dict


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


def fetch_imdb_images(name: str, limit: int = 10) -> List[Dict]:
    """
    Scrape IMDb public image stills / portraits.
    Safe for production (no selenium, no login).
    """

    search_url = f"https://www.imdb.com/find?q={name.replace(' ', '+')}&s=nm"

    r = requests.get(search_url, headers=HEADERS, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    result_link = soup.select_one(".result_text a")
    if not result_link or not result_link.get("href"):
        return []

    profile_url = f"https://www.imdb.com{result_link['href']}"
    images_url = f"{profile_url}mediaindex"

    r = requests.get(images_url, headers=HEADERS, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    images: List[Dict] = []

    for img in soup.select("img"):
        src = img.get("src")

        if not src:
            continue

        src_str = str(src)

        if "media-amazon" not in src_str:
            continue

        # Normalize to original resolution
        clean_url = src_str.split("_")[0] + ".jpg"

        images.append(
            {
                "title": "imdb_image",
                "image_url": clean_url,
                "page_url": images_url,
            }
        )

        if len(images) >= limit:
            break

    return images
