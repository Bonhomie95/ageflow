from __future__ import annotations

import argparse
from datetime import datetime, date

from .config.settings import settings
from .utils.logger import get_logger
from .utils.celebrity_queue import get_next_celebrity
from .utils.filesystem import read_json
from .facts.resolver import resolve_celebrity_facts

from .images.collector import (
    collect_images_for_celebrity,
    manifest_path,
)
from .images.anchor_selector import (
    select_anchors,
    save_anchor_timeline,
)
from .images.models import ImageManifest
from .utils.celebrity_queue import mark_used


log = get_logger("main")


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------


def extract_birth_year(birth_date: str | date) -> int:
    """
    Normalize birth_date to year (handles str or date).
    """
    if isinstance(birth_date, date):
        return birth_date.year

    # assume ISO string: YYYY-MM-DD
    return int(birth_date[:4])


# ---------------------------------------------------------------------
# STEP 2 — FACT RESOLUTION
# ---------------------------------------------------------------------


def run_resolve_once(force: bool = False) -> None:
    settings.ensure_dirs()

    name = get_next_celebrity()
    if not name:
        log.info("No celebrities left in queue (all used / queue empty).")
        return

    log.info(f"Resolving facts for: {name}")
    facts = resolve_celebrity_facts(name, force=force)

    log.info(
        f"✅ Facts resolved: {facts.name} | "
        f"DOB={facts.birth_date} | "
        f"target_year_end={facts.target_year_end}"
    )


# ---------------------------------------------------------------------
# STEP 3 — IMAGE COLLECTION
# ---------------------------------------------------------------------


def run_step3_collect_images(force: bool = False) -> None:
    settings.ensure_dirs()

    name = get_next_celebrity()
    if not name:
        log.info("No celebrities left in queue (all used / queue empty).")
        return

    facts = resolve_celebrity_facts(name, force=False)
    birth_year = extract_birth_year(facts.birth_date)

    log.info(
        f"Collecting images for: {facts.name} "
        f"(birth_year={birth_year}, target={facts.target_year_end})"
    )

    manifest = collect_images_for_celebrity(
        celebrity_name=facts.name,
        birth_year=birth_year,
        target_year_end=facts.target_year_end,
        force=force,
    )

    log.info(
        f"✅ Step3 complete: {facts.name} | "
        f"verified={manifest.verified_count} | "
        f"years={manifest.verified_years}"
    )


# ---------------------------------------------------------------------
# STEP 4 — ANCHOR SELECTION
# ---------------------------------------------------------------------


def run_step4_select_anchors() -> None:
    settings.ensure_dirs()

    name = get_next_celebrity()
    if not name:
        log.info("No celebrities left in queue.")
        return

    facts = resolve_celebrity_facts(name, force=False)
    birth_year = extract_birth_year(facts.birth_date)

    mp = manifest_path(facts.name)
    manifest = ImageManifest.model_validate(read_json(mp))

    anchors = select_anchors(
        manifest=manifest,
        birth_year=birth_year,
    )

    out = save_anchor_timeline(facts.name, anchors)
    mark_used(facts.name)
    log.info(f"✅ Marked as done: {facts.name}")


    log.info(f"✅ Anchors selected: {len(anchors)} → {out}")


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(prog="ageflow")

    parser.add_argument(
        "--resolve-once",
        action="store_true",
        help="Step2: Resolve next celebrity facts",
    )

    parser.add_argument(
        "--collect-images",
        action="store_true",
        help="Step3: Collect & verify images",
    )

    parser.add_argument(
        "--select-anchors",
        action="store_true",
        help="Step4: Select timeline anchors",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-run (ignore caches)",
    )

    args = parser.parse_args()

    if args.resolve_once:
        run_resolve_once(force=args.force)
        return

    if args.collect_images:
        run_step3_collect_images(force=args.force)
        return

    if args.select_anchors:
        run_step4_select_anchors()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
