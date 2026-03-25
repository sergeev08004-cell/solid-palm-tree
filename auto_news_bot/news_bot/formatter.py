from __future__ import annotations

import re
from datetime import timezone

from news_bot.models import CandidateItem


MULTI_PUNCTUATION_RE = re.compile(r"[!?]+")
EXTRA_SPACE_RE = re.compile(r"\s+")
CLICKBAIT_REPLACEMENTS = (
    ("сенсация", ""),
    ("шок", ""),
    ("эксклюзив", ""),
    ("лучший", ""),
    ("худший", ""),
    ("невероятный", ""),
    ("unbelievable", ""),
    ("exclusive", ""),
    ("best", ""),
    ("worst", "")
)
RUSSIAN_MONTHS = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря"
}


def format_post(item: CandidateItem, publication_title: str) -> str:
    return _format_post(item, publication_title=publication_title, summary_limit=360, max_length=4096)


def format_caption(item: CandidateItem, publication_title: str) -> str:
    return _format_post(item, publication_title=publication_title, summary_limit=220, max_length=1024)


def _format_post(item: CandidateItem, publication_title: str, summary_limit: int, max_length: int) -> str:
    title = neutralize_headline(item.title)
    summary = neutralize_text(item.summary)
    published = format_russian_date(item.published_at_utc.astimezone(timezone.utc))

    if summary:
        body = truncate(summary, summary_limit)
    else:
        body = "Опубликован новый материал по автомобильной теме."

    lines = [
        publication_title,
        item.topic_label,
        "",
        title,
        "",
        body,
        "",
        f"{item.source_name} | {published}",
        f"Подробнее: {item.url}"
    ]
    return truncate("\n".join(lines).strip(), max_length)


def neutralize_headline(text: str) -> str:
    cleaned = neutralize_text(text)
    return cleaned.rstrip(".")


def neutralize_text(text: str) -> str:
    cleaned = text.strip()
    for target, replacement in CLICKBAIT_REPLACEMENTS:
        cleaned = re.sub(rf"\b{re.escape(target)}\b", replacement, cleaned, flags=re.IGNORECASE)

    cleaned = MULTI_PUNCTUATION_RE.sub(".", cleaned)
    cleaned = cleaned.replace("« ", "«").replace(" »", "»")
    cleaned = EXTRA_SPACE_RE.sub(" ", cleaned).strip(" -–—.,")

    if not cleaned:
        return "Автомобильная новость"

    return cleaned[0].upper() + cleaned[1:]


def format_russian_date(value) -> str:
    month = RUSSIAN_MONTHS.get(value.month, str(value.month))
    return f"{value.day} {month} {value.year}, {value.strftime('%H:%M UTC')}"


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text

    snippet = text[:limit].rsplit(" ", 1)[0].strip()
    if not snippet:
        snippet = text[:limit].strip()
    return f"{snippet}..."
