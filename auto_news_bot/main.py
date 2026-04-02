#!/usr/bin/env python3

import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

from news_bot.config import load_config
from news_bot.formatter import detect_brand_label, format_caption, format_post
from news_bot.page_content import fetch_page_story
from news_bot.page_images import fetch_page_images, fetch_page_videos
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

        item = enrich_item_content(item, config, verbose=verbose)
        item, image_urls, video_url = enrich_item_media(item, config, verbose=verbose)
        item = localize_item(item, translator, verbose=verbose)
        if not video_url and not image_urls:
            if verbose:
                print(f"[media] source={item.source_name} skipped: no video or photo")
            continue
        message = format_post(item, config.telegram.channel_id)
        caption = format_caption(item, config.telegram.channel_id)
        album_label = detect_brand_label(item)
        if dry_run:
            print("=" * 72)
            print(message)
            if video_url:
                print("")
                print(f"Видео: {video_url}")
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
                    video_url=video_url,
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


def enrich_item_media(item, config, verbose: bool = False):
    images = []
    if item.image_url:
        images.append(item.image_url)
    videos = []
    if item.video_url:
        videos.append(item.video_url)

    try:
        page_videos = fetch_page_videos(item.url, config, limit=2)
    except Exception as error:
        if verbose:
            print(f"[video] source={item.source_name} error={error}")
        page_videos = []

    for video_url in page_videos:
        if video_url not in videos:
            videos.append(video_url)

    try:
        page_images = fetch_page_images(item.url, config, limit=6)
    except Exception as error:
        if verbose:
            print(f"[image] source={item.source_name} error={error}")
        page_images = []

    for image_url in page_images:
        if image_url not in images:
            images.append(image_url)

    primary_video = videos[0] if videos else item.video_url
    primary_image = images[0] if images else item.image_url

    if verbose:
        if primary_video:
            print(f"[video] source={item.source_name} videos={len(videos)} first={primary_video}")
        if primary_image:
            print(f"[image] source={item.source_name} images={len(images)} first={primary_image}")

    return replace(item, image_url=primary_image, video_url=primary_video), images, primary_video


def enrich_item_content(item, config, verbose: bool = False):
    try:
        page_story = fetch_page_story(item.url, config, max_paragraphs=6)
    except Exception as error:
        if verbose:
            print(f"[content] source={item.source_name} error={error}")
        return item

    if not page_story:
        return item

    current_summary = (item.summary or "").strip()
    if len(page_story) <= len(current_summary):
        return item

    merged_parts = []
    title_normalized = normalize_merge_text(item.title)
    existing_norms: list[str] = []
    if current_summary:
        current_normalized = normalize_merge_text(current_summary)
        if current_normalized and current_normalized not in normalize_merge_text(page_story):
            merged_parts.append(current_summary)
            existing_norms.append(current_normalized)

    for paragraph in page_story.split("\n\n"):
        cleaned = paragraph.strip()
        if not cleaned:
            continue
        normalized = normalize_merge_text(cleaned)
        if not normalized:
            continue
        if title_normalized and normalized.startswith(title_normalized) and len(normalized) <= len(title_normalized) + 220:
            continue
        if any(
            (normalized in existing or existing in normalized) and min(len(normalized), len(existing)) >= 80
            for existing in existing_norms
        ):
            continue
        merged_parts.append(cleaned)
        existing_norms.append(normalized)

    merged_summary = "\n\n".join(merge_short_paragraphs(merged_parts)).strip()
    if not merged_summary:
        return item

    if verbose:
        print(f"[content] source={item.source_name} summary={len(current_summary)} enriched={len(merged_summary)}")

    return replace(item, summary=merged_summary)


def normalize_merge_text(value: str) -> str:
    return " ".join((value or "").lower().split())


def merge_short_paragraphs(paragraphs: list[str]) -> list[str]:
    merged: list[str] = []
    for paragraph in paragraphs:
        cleaned = paragraph.strip()
        if not cleaned:
            continue
        if merged and len(cleaned) < 65:
            merged[-1] = f"{merged[-1]} {cleaned}".strip()
            continue
        merged.append(cleaned)
    return merged


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
