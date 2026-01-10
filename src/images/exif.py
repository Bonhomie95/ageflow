from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ExifTags


# Common EXIF date tags
_EXIF_DATE_TAGS = {"DateTimeOriginal", "DateTimeDigitized", "DateTime"}


def _normalize_exif_datetime(value: str) -> Optional[str]:
    """
    EXIF usually: "YYYY:MM:DD HH:MM:SS"
    Normalize to YYYY-MM-DD if possible.
    """
    if not value or not isinstance(value, str):
        return None
    v = value.strip()
    # Typical: 2019:05:17 13:44:02
    try:
        dt = datetime.strptime(v, "%Y:%m:%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    # Sometimes already ISO-ish
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(v, fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue

    return None


def extract_exif_date(path: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns: (date_yyyy_mm_dd, method_tag)
    method_tag is one of DateTimeOriginal/DateTimeDigitized/DateTime
    """
    try:
        img = Image.open(path)
        exif = img.getexif()
        if not exif:
            return None, None

        tag_map = {}
        for k, v in ExifTags.TAGS.items():
            tag_map[v] = k

        for tag_name in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
            tag_id = tag_map.get(tag_name)
            if not tag_id:
                continue
            raw = exif.get(tag_id)
            norm = _normalize_exif_datetime(raw) if raw else None
            if norm:
                return norm, tag_name

        return None, None
    except Exception:
        return None, None
