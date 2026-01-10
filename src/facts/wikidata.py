from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

import requests

from ..config.settings import settings


@dataclass
class WikidataFacts:
    wikidata_id: str
    birth_date: Optional[str]  # YYYY-MM-DD
    occupations: list[str]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": settings.user_agent})
    return s


def fetch_entity(wikidata_id: str) -> Dict[str, Any]:
    s = _session()
    url = "https://www.wikidata.org/wiki/Special:EntityData/{}.json".format(wikidata_id)
    r = s.get(url, timeout=settings.http_timeout)
    r.raise_for_status()
    return r.json()


def _first_time_claim(entity: Dict[str, Any], prop: str) -> Optional[str]:
    """
    Extracts first time value from claims (e.g. P569 date of birth).
    Returns ISO date YYYY-MM-DD if possible.
    """
    claims = (
        (entity.get("entities") or {}).get(next(iter(entity.get("entities", {}))), {})
        or {}
    ).get("claims") or {}
    arr = claims.get(prop) or []
    for c in arr:
        mainsnak = c.get("mainsnak") or {}
        datavalue = mainsnak.get("datavalue") or {}
        value = datavalue.get("value") or {}
        time_str = value.get("time")
        if time_str and isinstance(time_str, str):
            # Format like "+1974-11-11T00:00:00Z"
            # We normalize to YYYY-MM-DD
            t = time_str.lstrip("+")
            if "T" in t:
                t = t.split("T")[0]
            if len(t) >= 10:
                return t[:10]
    return None


def _extract_occupations(entity: Dict[str, Any]) -> list[str]:
    # Occupation property P106 points to other Q-ids; we can keep labels later if needed.
    # For now return empty or Q-ids; resolver can keep raw.
    claims = (
        (entity.get("entities") or {}).get(next(iter(entity.get("entities", {}))), {})
        or {}
    ).get("claims") or {}
    occ = []
    for c in claims.get("P106", []) or []:
        dv = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {}
        qid = dv.get("id")
        if qid:
            occ.append(qid)
    return occ


def get_facts(wikidata_id: str) -> WikidataFacts:
    data = fetch_entity(wikidata_id)
    entity = data  # contains "entities"
    birth_date = _first_time_claim(entity, "P569")
    occupations = _extract_occupations(entity)
    return WikidataFacts(
        wikidata_id=wikidata_id, birth_date=birth_date, occupations=occupations
    )
