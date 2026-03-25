from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from news_bot.config import AppConfig
from news_bot.feeds import fetch_feed
from news_bot.storage import Storage
from news_bot.text_tools import fingerprint_from_text, normalize_url, title_key, tokens_from_text


@dataclass(frozen=True)
class CollectedItem:
    source_name: str
    source_group: str
    source_language: str
    source_weight: float
    title: str
    title_key: str
    summary: str
    url: str
    image_url: str
    published_at: datetime
    fingerprint: str
    tokens: List[str]


def collect_candidates(config: AppConfig, storage: Storage, verbose: bool = False) -> List[CollectedItem]:
    collected: List[CollectedItem] = []

    for source in config.sources:
        if not source.enabled:
            continue

        try:
            entries = fetch_feed(source, config)
            if verbose:
                print(f"[fetch] source={source.name} entries={len(entries)}")
        except Exception as error:
            if verbose:
                print(f"[fetch] source={source.name} error={error}")
            continue

        for entry in entries:
            item_title_key = title_key(entry.title)
            fingerprint = fingerprint_from_text(entry.source_name, entry.title, entry.url)
            if storage.was_published(fingerprint) or storage.looks_like_published(item_title_key, normalize_url(entry.url)):
                continue

            lowered_haystack = f"{entry.title} {entry.summary}".lower()
            if any(keyword in lowered_haystack for keyword in config.blocked_keywords):
                continue

            tokens = tokens_from_text(f"{entry.title} {entry.summary}")
            if len(tokens) < 4:
                continue

            collected.append(
                CollectedItem(
                    source_name=entry.source_name,
                    source_group=entry.source_group,
                    source_language=entry.source_language,
                    source_weight=entry.source_weight,
                    title=entry.title,
                    title_key=item_title_key,
                    summary=entry.summary,
                    url=entry.url,
                    image_url=entry.image_url,
                    published_at=entry.published_at,
                    fingerprint=fingerprint,
                    tokens=tokens
                )
            )

    return collected
