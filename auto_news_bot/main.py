#!/usr/bin/env python3

import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

from news_bot.config import load_config
from news_bot.formatter import format_caption, format_post
from news_bot.page_images import fetch_page_image
from news_bot.ranking import rank_candidates
from news_bot.storage import Storage
from news_bot.telegram_api import TelegramPublisher
from news_bot.translation import Translator
from news_bot.worker import collect_candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto automotive news Telegram bot")
    parser.add_argument("--config", default="config.json", help="Path to JSON config file")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--dry-run", action="store_true", help="Do not publish to Telegram")
    parser.add_argument("--verbose", action="store_true", help="Print extended cycle logs")
    return parser.parse_args()


def run_cycle(storage: Storage, publisher: TelegramPublisher, dry_run: bool, verbose: bool) -> int:
    config = publisher.config
    translator = Translator(config)
    candidates = collect_candidates(config, storage, verbose=verbose)
    ranked = rank_candidates(
        candidates,
        storage=storage,
        priority_topics=config.priority_topics,
        max_age_hours=config.max_post_age_hours,
        min_age_minutes=config.min_post_age_minutes
    )

    if verbose:
        print(f"[cycle] candidates={len(candidates)} ranked={len(ranked)} dry_run={dry_run}")

    published = 0
    for item in ranked:
        if published >= config.max_posts_per_cycle:
            break

        if not dry_run and not storage.can_publish_now(config.min_publish_gap_minutes):
            if verbose:
                print("[cycle] publish gap active, postponing remaining items")
            break

        item = enrich_item_image(item, config, verbose=verbose)
        item = localize_item(item, translator, verbose=verbose)
        message = format_post(item, config.publication_title)
        caption = format_caption(item, config.publication_title)
        if dry_run:
            print("=" * 72)
            print(message)
            if item.image_url:
                print("")
                print(f"Картинка: {item.image_url}")
            print("=" * 72)
        else:
            publisher.publish(message, image_url=item.image_url, caption=caption)
            storage.mark_published(item)

        published += 1

        if verbose:
            action = "prepared" if dry_run else "published"
            print(f"[cycle] {action} fingerprint={item.fingerprint} source={item.source_name}")

    if verbose and published == 0:
        print("[cycle] nothing published")

    return published


def localize_item(item, translator: Translator, verbose: bool = False):
    if not translator.should_translate(item.source_language):
        return item

    try:
        translated_title = translator.translate_text(item.title, item.source_language)
        translated_summary = translator.translate_text(item.summary, item.source_language)
    except Exception as error:
        if verbose:
            print(f"[translate] source={item.source_name} error={error}")
        return item

    if verbose:
        print(f"[translate] source={item.source_name} translated to {translator.config.translation.target_language}")

    return replace(
        item,
        source_language=translator.config.translation.target_language,
        title=translated_title,
        summary=translated_summary
    )


def enrich_item_image(item, config, verbose: bool = False):
    if item.image_url:
        return item

    try:
        image_url = fetch_page_image(item.url, config)
    except Exception as error:
        if verbose:
            print(f"[image] source={item.source_name} error={error}")
        return item

    if not image_url:
        if verbose:
            print(f"[image] source={item.source_name} no image found for {item.url}")
        return item

    if verbose:
        print(f"[image] source={item.source_name} image={image_url}")

    return replace(item, image_url=image_url)


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()
    config = load_config(config_path)
    storage = Storage(config_path.parent / config.database_path)
    publisher = TelegramPublisher(config)

    if args.once:
        run_cycle(storage, publisher, dry_run=args.dry_run, verbose=args.verbose)
        return 0

    while True:
        try:
            run_cycle(storage, publisher, dry_run=args.dry_run, verbose=args.verbose)
        except KeyboardInterrupt:
            return 0
        except Exception as error:
            print(f"[error] {error}", file=sys.stderr)

        time.sleep(config.poll_interval_minutes * 60)


if __name__ == "__main__":
    raise SystemExit(main())
