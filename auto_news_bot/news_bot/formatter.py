from __future__ import annotations

import html
import re
from datetime import timezone
from urllib.parse import urlsplit

from news_bot.models import CandidateItem


MULTI_PUNCTUATION_RE = re.compile(r"[!?]+")
EXTRA_SPACE_RE = re.compile(r"\s+")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
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
TOPIC_EMOJIS = {
    "recalls": "⚠️",
    "law": "📜",
    "new_models": "🚗",
    "prices": "💵",
    "sales": "📈",
    "production": "🏭",
    "electric": "⚡",
    "technology": "🧠",
    "industry": "🌍"
}
TOPIC_HASHTAGS = {
    "recalls": "Отзыв",
    "law": "Регулирование",
    "new_models": "НоваяМодель",
    "prices": "Цены",
    "sales": "Рынок",
    "production": "Производство",
    "electric": "Электрокары",
    "technology": "Технологии",
    "industry": "Автоновости"
}
BRAND_TAGS = (
    ("mercedes-benz", "MercedesBenz"),
    ("mercedes", "Mercedes"),
    ("general motors", "GM"),
    ("alfa romeo", "AlfaRomeo"),
    ("land rover", "LandRover"),
    ("rolls-royce", "RollsRoyce"),
    ("rolls royce", "RollsRoyce"),
    ("aston martin", "AstonMartin"),
    ("volkswagen", "Volkswagen"),
    ("toyota", "Toyota"),
    ("tesla", "Tesla"),
    ("bmw", "BMW"),
    ("mini", "MINI"),
    ("audi", "Audi"),
    ("porsche", "Porsche"),
    ("hyundai", "Hyundai"),
    ("kia", "Kia"),
    ("ford", "Ford"),
    ("nissan", "Nissan"),
    ("honda", "Honda"),
    ("mazda", "Mazda"),
    ("subaru", "Subaru"),
    ("lexus", "Lexus"),
    ("volvo", "Volvo"),
    ("byd", "BYD"),
    ("geely", "Geely"),
    ("zeekr", "Zeekr"),
    ("xpeng", "XPeng"),
    ("nio", "NIO"),
    ("chery", "Chery"),
    ("ferrari", "Ferrari"),
    ("lamborghini", "Lamborghini"),
    ("bugatti", "Bugatti"),
    ("renault", "Renault"),
    ("peugeot", "Peugeot"),
    ("citroen", "Citroen"),
    ("skoda", "Skoda"),
    ("seat", "SEAT"),
    ("jeep", "Jeep"),
    ("ram", "Ram"),
    ("gmc", "GMC"),
    ("cadillac", "Cadillac"),
    ("chevrolet", "Chevrolet"),
    ("dodge", "Dodge"),
    ("rivian", "Rivian"),
    ("lucid", "Lucid"),
    ("polestar", "Polestar"),
    ("stellantis", "Stellantis")
)
SOURCE_TAGS = {
    "insideevs": "InsideEVs",
    "motorauthority": "MotorAuthority",
    "thecarconnection": "TheCarConnection",
    "greencarreports": "GreenCarReports",
    "autoevolution": "Autoevolution",
    "bmwgroup": "BMW",
    "hyundai": "Hyundai",
    "drom": "Drom"
}


def format_post(item: CandidateItem, publication_title: str) -> str:
    return _format_post(
        item,
        publication_title=publication_title,
        summary_limit=520,
        max_length=4096,
        max_bullets=3,
        include_spoiler=True
    )


def format_caption(item: CandidateItem, publication_title: str) -> str:
    return _format_post(
        item,
        publication_title=publication_title,
        summary_limit=280,
        max_length=1024,
        max_bullets=2,
        include_spoiler=False
    )


def _format_post(
    item: CandidateItem,
    publication_title: str,
    summary_limit: int,
    max_length: int,
    max_bullets: int,
    include_spoiler: bool
) -> str:
    title = neutralize_headline(item.title)
    summary = truncate(neutralize_text(item.summary), summary_limit)
    published = format_russian_date(item.published_at_utc.astimezone(timezone.utc))
    emoji = TOPIC_EMOJIS.get(item.topic, "📰")

    lead, bullets = build_story_blocks(summary, max_bullets=max_bullets)
    tags = build_hashtags(item, title)
    lines = [
        f"{emoji} <b>{escape_text(publication_title)}</b>",
        "",
        f"<b>{escape_text(title)}</b>"
    ]

    if lead:
        lines.extend(
            [
                "",
                f"<i>{escape_text(lead)}</i>"
            ]
        )

    if bullets:
        lines.extend(
            [
                "",
                "<b>Что известно:</b>"
            ]
        )
        lines.extend(f"• {escape_text(bullet)}" for bullet in bullets)
    elif summary and summary.lower() != lead.lower():
        lines.extend(
            [
                "",
                escape_text(summary)
            ]
        )
    elif not summary:
        lines.extend(
            [
                "",
                "Опубликован новый материал по автомобильной теме."
            ]
        )

    if item.duplicate_count > 1:
        lines.extend(
            [
                "",
                f"📌 <i>Сюжет подтвержден {item.duplicate_count} источниками</i>"
            ]
        )

    lines.extend(
        [
            "",
            f"📰 <b>Источник:</b> {escape_text(item.source_name)}",
            f"🕒 <i>{escape_text(published)}</i>",
            f"🔗 <a href=\"{escape_attr(item.url)}\">Читать полностью</a>"
        ]
    )

    if tags:
        lines.extend(
            [
                "",
                " ".join(f"#{tag}" for tag in tags)
            ]
        )

    if include_spoiler:
        original_label = source_label(item)
        lines.extend(
            [
                "",
                f"<tg-spoiler>Оригинал: {escape_text(original_label)}</tg-spoiler>"
            ]
        )

    text = "\n".join(lines).strip()
    if len(text) <= max_length:
        return text

    trimmed_bullets = bullets[: max(1, max_bullets - 1)]
    fallback_lines = [
        f"{emoji} <b>{escape_text(publication_title)}</b>",
        "",
        f"<b>{escape_text(title)}</b>"
    ]
    if lead:
        fallback_lines.extend(
            [
                "",
                f"<i>{escape_text(truncate(lead, 180))}</i>"
            ]
        )
    if trimmed_bullets:
        fallback_lines.extend(
            [
                "",
                "<b>Что известно:</b>"
            ]
        )
        fallback_lines.extend(f"• {escape_text(truncate(bullet, 140))}" for bullet in trimmed_bullets)

    fallback_lines.extend(
        [
            "",
            f"📰 <b>Источник:</b> {escape_text(item.source_name)}",
            f"🕒 <i>{escape_text(published)}</i>",
            f"🔗 <a href=\"{escape_attr(item.url)}\">Читать полностью</a>"
        ]
    )
    if tags:
        fallback_lines.extend(["", " ".join(f"#{tag}" for tag in tags[:2])])

    return truncate("\n".join(fallback_lines).strip(), max_length)


def build_story_blocks(summary: str, max_bullets: int) -> tuple[str, list[str]]:
    if not summary:
        return "", []

    sentences = [neutralize_text(part) for part in SENTENCE_SPLIT_RE.split(summary) if part.strip()]
    if not sentences:
        clean_summary = neutralize_text(summary)
        return clean_summary, []

    lead = truncate(sentences[0], 190)
    bullets: list[str] = []

    for sentence in sentences[1:]:
        bullet = truncate(sentence, 140)
        if bullet and bullet.lower() != lead.lower():
            bullets.append(bullet)
        if len(bullets) >= max_bullets:
            break

    if not bullets and len(sentences) == 1 and len(lead) > 170:
        shortened = truncate(lead, 120)
        if shortened != lead:
            bullets.append(lead[len(shortened):].strip(" .,;:-"))
            lead = shortened

    return lead, [bullet for bullet in bullets if bullet]


def build_hashtags(item: CandidateItem, title: str) -> list[str]:
    haystack = f"{title} {item.summary} {item.source_name}".lower()
    tags: list[str] = []

    for phrase, tag in BRAND_TAGS:
        if phrase in haystack and tag not in tags:
            tags.append(tag)
        if len(tags) >= 2:
            break

    source_tag = SOURCE_TAGS.get(item.source_group)
    if source_tag and source_tag not in tags:
        tags.append(source_tag)

    topic_tag = TOPIC_HASHTAGS.get(item.topic, "Автоновости")
    if topic_tag not in tags:
        tags.append(topic_tag)

    return tags[:3]


def source_label(item: CandidateItem) -> str:
    host = urlsplit(item.url).netloc.lower().lstrip("www.")
    if host:
        return f"{item.source_name} • {host}"
    return item.source_name


def escape_text(value: str) -> str:
    return html.escape(value, quote=False)


def escape_attr(value: str) -> str:
    return html.escape(value, quote=True)


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
