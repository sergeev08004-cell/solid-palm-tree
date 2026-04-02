#!/usr/bin/env python3

import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

from news_bot.config import load_config
from news_bot.formatter import detect_brand_label, format_caption, format_post
from news_bot.page_images import fetch_page_images
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
    rank_window = max(config.max_posts_per_cycle * 4, config.max_posts_per_cycle + 5)
    ranked = rank_candidates(
        candidates,
        storage=storage,
        priority_topics=config.priority_topics,
        max_age_hours=config.max_post_age_hours,
        min_age_minutes=config.min_post_age_minutes,
        max_items=rank_window,
        diversity=config.diversity
    )

    if verbose:
        print(f"[cycle] candidates={len(candidates)} ranked={len(ranked)} dry_run={dry_run}")

    published = 0
    publish_errors = 0
    last_publish_error: Exception | None = None
    for item in ranked:
        if published >= config.max_posts_per_cycle:
            break

        if not dry_run and not storage.can_publish_now(config.min_publish_gap_minutes):
            if verbose:
                print("[cycle] publish gap active, postponing remaining items")
            break

        item, image_urls = enrich_item_images(item, config, verbose=verbose)
        item = localize_item(item, translator, verbose=verbose)
        message = format_post(item, config.publication_title)
        caption = format_caption(item, config.publication_title)
        album_label = detect_brand_label(item)
        if dry_run:
            print("=" * 72)
            print(message)
            if image_urls:
                print("")
                for index, image_url in enumerate(image_urls, start=1):
                    print(f"Картинка {index}: {image_url}")
                    if index in (2, 3):
                        print(f"Подпись {index}: {album_label}")
            print("=" * 72)
        else:
            try:
                publisher.publish(
                    message,
                    image_url=item.image_url,
                    image_urls=image_urls,
                    caption=caption,
                    album_label=album_label
                )
            except Exception as error:
                publish_errors += 1
                last_publish_error = error
                if verbose:
                    print(f"[publish] source={item.source_name} error={error}")
                continue
            storage.mark_published(item)

        published += 1

        if verbose:
            action = "prepared" if dry_run else "published"
            print(f"[cycle] {action} fingerprint={item.fingerprint} source={item.source_name}")

    if verbose and published == 0:
        print("[cycle] nothing published")

    if not dry_run and published == 0 and publish_errors > 0 and last_publish_error is not None:
        raise RuntimeError(f"Unable to publish any items: {last_publish_error}")

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


def enrich_item_images(item, config, verbose: bool = False):
    images = []
    if item.image_url:
        images.append(item.image_url)

    try:
        page_images = fetch_page_images(item.url, config, limit=4)
    except Exception as error:
        if verbose:
            print(f"[image] source={item.source_name} error={error}")
        return item, images

    for image_url in page_images:
        if image_url not in images:
            images.append(image_url)

    if not images:
        if verbose:
            print(f"[image] source={item.source_name} no image found for {item.url}")
        return item, []

    if verbose:
        print(f"[image] source={item.source_name} images={len(images)} first={images[0]}")

    primary_image = images[0]
    if item.image_url == primary_image:
        return item, images

    return replace(item, image_url=primary_image), images


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
