from __future__ import annotations

import argparse

from .config.settings import settings
from .utils.logger import get_logger
from .utils.celebrity_queue import get_next_celebrity
from .facts.resolver import resolve_celebrity_facts
from .images.collector import collect_images_for_celebrity

log = get_logger("main")


def run_resolve_once(force: bool = False) -> None:
    settings.ensure_dirs()
    name = get_next_celebrity()
    if not name:
        log.info("No celebrities left in queue (all used / queue empty).")
        return

    log.info(f"Resolving facts for: {name}")
    facts = resolve_celebrity_facts(name, force=force)
    log.info(
        f"✅ Facts: {facts.name} | DOB={facts.birth_date} | target_year_end={facts.target_year_end}"
    )


def run_step3_collect_images(force: bool = False) -> None:
    settings.ensure_dirs()
    name = get_next_celebrity()
    if not name:
        log.info("No celebrities left in queue (all used / queue empty).")
        return

    # Ensure facts exist
    facts = resolve_celebrity_facts(name, force=False)

    log.info(
        f"Collecting images for: {facts.name} (must reach {facts.target_year_end-1}/{facts.target_year_end})"
    )
    manifest = collect_images_for_celebrity(
        celebrity_name=facts.name,
        target_year_end=facts.target_year_end,
        force=force,
        commons_limit=25,
        serpapi_limit=25,
    )
    log.info(
        f"✅ Step3 done: {facts.name} | verified={manifest.verified_count} | years={manifest.verified_years}"
    )


def main():
    parser = argparse.ArgumentParser(prog="ageflow")
    parser.add_argument(
        "--resolve-once",
        action="store_true",
        help="Step2: Resolve next celebrity in queue",
    )
    parser.add_argument(
        "--collect-images",
        action="store_true",
        help="Step3: Collect & verify images for next celebrity",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-run (ignore cache where applicable)",
    )
    args = parser.parse_args()

    if args.resolve_once:
        run_resolve_once(force=args.force)
        return

    if args.collect_images:
        run_step3_collect_images(force=args.force)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
