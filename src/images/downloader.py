from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

import requests

from ..config.settings import settings


def download_file(
    url: str, out_path: Path, timeout: Optional[int] = None, retries: int = 3
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    s = requests.Session()
    s.headers.update({"User-Agent": settings.user_agent})

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            r = s.get(url, stream=True, timeout=timeout or settings.http_timeout)
            r.raise_for_status()

            tmp = out_path.with_suffix(out_path.suffix + ".part")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)

            os.replace(tmp, out_path)
            return
        except Exception as e:
            last_err = e
            time.sleep(0.6 * attempt)

    raise RuntimeError(
        f"Failed to download after {retries} attempts: {url} | {last_err}"
    )
