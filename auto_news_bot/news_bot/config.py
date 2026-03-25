from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class SourceConfig:
    name: str
    url: str
    language: str
    weight: float
    enabled: bool = True


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    channel_id: str
    disable_web_page_preview: bool = False


@dataclass(frozen=True)
class TranslationConfig:
    enabled: bool
    provider: str
    target_language: str
    source_languages: List[str]


@dataclass(frozen=True)
class AppConfig:
    telegram: TelegramConfig
    poll_interval_minutes: int
    max_posts_per_cycle: int
    min_post_age_minutes: int
    max_post_age_hours: int
    min_publish_gap_minutes: int
    request_timeout_seconds: int
    database_path: str
    user_agent: str
    publication_title: str
    sources: List[SourceConfig]
    priority_topics: List[str]
    blocked_keywords: List[str]
    translation: TranslationConfig


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}. Copy config.example.json to config.json first."
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    telegram_payload = payload["telegram"]
    telegram = TelegramConfig(
        bot_token=telegram_payload["bot_token"],
        channel_id=telegram_payload["channel_id"],
        disable_web_page_preview=bool(telegram_payload.get("disable_web_page_preview", False))
    )
    translation_payload = payload.get("translation", {})
    translation = TranslationConfig(
        enabled=bool(translation_payload.get("enabled", False)),
        provider=str(translation_payload.get("provider", "google_web")),
        target_language=str(translation_payload.get("target_language", "ru")),
        source_languages=[str(item).lower() for item in translation_payload.get("source_languages", ["en"])]
    )

    sources = [
        SourceConfig(
            name=source["name"],
            url=source["url"],
            language=source.get("language", "ru"),
            weight=float(source.get("weight", 1.0)),
            enabled=bool(source.get("enabled", True))
        )
        for source in payload.get("sources", [])
    ]

    if not telegram.bot_token or "PASTE_TELEGRAM_BOT_TOKEN_HERE" in telegram.bot_token:
        raise ValueError("Fill telegram.bot_token in config.json")

    if not telegram.channel_id:
        raise ValueError("Fill telegram.channel_id in config.json")

    if not sources:
        raise ValueError("Add at least one enabled source to config.json")

    return AppConfig(
        telegram=telegram,
        poll_interval_minutes=int(payload.get("poll_interval_minutes", 30)),
        max_posts_per_cycle=int(payload.get("max_posts_per_cycle", 3)),
        min_post_age_minutes=int(payload.get("min_post_age_minutes", 5)),
        max_post_age_hours=int(payload.get("max_post_age_hours", 24)),
        min_publish_gap_minutes=int(payload.get("min_publish_gap_minutes", 20)),
        request_timeout_seconds=int(payload.get("request_timeout_seconds", 20)),
        database_path=str(payload.get("database_path", "data/news.db")),
        user_agent=str(payload.get("user_agent", "AutoNewsBot/1.0")),
        publication_title=str(payload.get("publication_title", "Мировые автоновости")),
        sources=sources,
        priority_topics=list(payload.get("priority_topics", [])),
        blocked_keywords=[item.lower() for item in payload.get("blocked_keywords", [])],
        translation=translation
    )
