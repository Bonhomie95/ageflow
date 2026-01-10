from __future__ import annotations

from pathlib import Path

from ..config.settings import settings
from ..utils.slug import slugify
from ..utils.filesystem import read_json, write_json
from ..utils.logger import get_logger

from .models import CelebrityFacts, SourceFlags
from .wikipedia import search_best_title, resolve_page
from .wikidata import get_facts
from .validator import validate_birth_date

log = get_logger("facts")


def facts_path_for(name: str) -> Path:
    return settings.facts_dir / f"{slugify(name)}.json"


def resolve_celebrity_facts(name: str, force: bool = False) -> CelebrityFacts:
    settings.ensure_dirs()

    out_path = facts_path_for(name)
    if out_path.exists() and not force:
        cached = read_json(out_path)
        return CelebrityFacts.model_validate(cached)

    # 1) Wikipedia title
    title = search_best_title(name)
    if not title:
        raise ValueError(f"Could not find a Wikipedia title for: {name}")

    # 2) Resolve Wikipedia page + Wikidata Q-id
    wp = resolve_page(title)
    if not wp.wikidata_id:
        raise ValueError(f"No Wikidata id found for Wikipedia page: {wp.title}")

    # 3) Wikidata DOB
    wd = get_facts(wp.wikidata_id)
    v = validate_birth_date(wd.birth_date)
    if not v.ok:
        raise ValueError(f"Facts validation failed for '{name}': {v.reason}")

    facts = CelebrityFacts(
        name=name,
        slug=slugify(name),
        wikipedia_title=wp.title,
        wikipedia_url=wp.url,
        wikidata_id=wp.wikidata_id,
        birth_date=wd.birth_date or "",
        confidence=float(v.confidence),
        target_year_end=settings.target_year_end,
        sources=SourceFlags(wikipedia=True, wikidata=True),
        timeline=[],  # Step 3 will build a date-backed photo timeline from sources
        raw={
            "wikipedia": {
                "description": wp.description,
                "extract": wp.extract,
                "pageid": wp.pageid,
            },
            "wikidata": {
                "occupations_qids": wd.occupations,
            },
        },
    )

    write_json(out_path, facts.model_dump())
    log.info(f"✅ facts cached → {out_path.as_posix()}")
    return facts
