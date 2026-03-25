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
    "autocar": "Autocar",
    "insideevs": "InsideEVs",
    "motorauthority": "MotorAuthority",
    "thecarconnection": "TheCarConnection",
    "greencarreports": "GreenCarReports",
    "autoevolution": "Autoevolution",
    "bmwgroup": "BMW",
    "hyundai": "Hyundai",
    "drom": "Drom",
    "motorru": "MotorRu"
}
SPEC_FOCUS_TOPICS = {"new_models", "electric"}
GADGET_KEYWORDS = (
    "гаджет",
    "устройств",
    "девайс",
    "аксессуар",
    "видеорегистратор",
    "dashcam",
    "head-up",
    "head unit",
    "carplay",
    "android auto",
    "экран",
    "диспле",
    "display",
    "screen",
    "камера",
    "camera",
    "зарядн",
    "charger",
    "charging pad",
    "адаптер",
    "навигатор",
    "смарт-зеркал",
    "smart mirror"
)
MODEL_KEYWORDS = (
    "кроссовер",
    "седан",
    "купе",
    "хэтчбек",
    "универсал",
    "внедорожник",
    "пикап",
    "минивэн",
    "van",
    "suv",
    "crossover",
    "sedan",
    "wagon",
    "pickup",
    "hatchback"
)
POWER_RE = re.compile(r"(?P<value>\d{2,4}(?:[.,]\d+)?)\s*(?P<unit>л\.?\s*с\.?|hp|bhp|кВт|kw)\b", re.IGNORECASE)
BATTERY_RE = re.compile(r"(?P<value>\d{1,3}(?:[.,]\d+)?)\s*(?P<unit>кВт(?:·|-|\s)?ч|kwh)\b", re.IGNORECASE)
RANGE_PATTERNS = (
    re.compile(
        r"(?:запас(?:ом)? хода|range|wltp|epa|cltc|пробег(?:а)?)(?:[^0-9]{0,24})(?P<value>\d{2,4})\s*(?P<unit>км|km)\b",
        re.IGNORECASE
    ),
    re.compile(
        r"(?P<value>\d{2,4})\s*(?P<unit>км|km)\b(?:[^0-9]{0,24})(?:запас(?:ом)? хода|range|wltp|epa|cltc|пробег(?:а)?)",
        re.IGNORECASE
    )
)
ACCELERATION_RE = re.compile(
    r"0\s*[-–—]\s*100\s*(?:км/ч|km/h)?\s*(?:за|in)?\s*(?P<value>\d{1,2}(?:[.,]\d+)?)\s*(?:с|секунд\w*|sec|seconds)\b",
    re.IGNORECASE
)
CHARGING_PATTERNS = (
    re.compile(
        r"(?:зарядк\w*|charging(?: power)?|dc fast|быстр\w* заряд\w*)(?:[^0-9]{0,24})(?P<value>\d{2,4}(?:[.,]\d+)?)\s*(?:кВт|kw)\b",
        re.IGNORECASE
    ),
    re.compile(
        r"(?P<value>\d{2,4}(?:[.,]\d+)?)\s*(?:кВт|kw)\b(?:[^0-9]{0,24})(?:зарядк\w*|charging(?: power)?|dc fast|быстр\w* заряд\w*)",
        re.IGNORECASE
    )
)
TORQUE_RE = re.compile(r"(?P<value>\d{2,4}(?:[.,]\d+)?)\s*(?:Нм|nm)\b", re.IGNORECASE)
ENGINE_PATTERNS = (
    re.compile(
        r"(?:двигател\w*|turbo|motor|v6|v8|рядн\w*)(?:[^0-9]{0,20})(?P<value>\d(?:[.,]\d)?)\s*(?:л|литр\w*)\b",
        re.IGNORECASE
    ),
    re.compile(
        r"(?P<value>\d(?:[.,]\d)?)\s*(?:л|литр\w*)\b(?:[^0-9]{0,20})(?:двигател\w*|turbo|motor|v6|v8|рядн\w*)",
        re.IGNORECASE
    )
)
SCREEN_PATTERNS = (
    re.compile(
        r"(?:экран|диспле\w*|display|screen)(?:[^0-9]{0,20})(?P<value>\d{1,2}(?:[.,]\d+)?)\s*(?:дюйм(?:а|ов)?|inch(?:es)?|\")",
        re.IGNORECASE
    ),
    re.compile(
        r"(?P<value>\d{1,2}(?:[.,]\d+)?)\s*(?:дюйм(?:а|ов)?|inch(?:es)?|\")(?:[^0-9]{0,20})(?:экран|диспле\w*|display|screen)",
        re.IGNORECASE
    )
)
MEMORY_PATTERNS = (
    re.compile(
        r"(?:памят\w*|storage|ram|оператив\w*)(?:[^0-9]{0,20})(?P<value>\d{1,4})\s*(?P<unit>ГБ|GB|ТБ|TB)\b",
        re.IGNORECASE
    ),
    re.compile(
        r"(?P<value>\d{1,4})\s*(?P<unit>ГБ|GB|ТБ|TB)\b(?:[^0-9]{0,20})(?:памят\w*|storage|ram|оператив\w*)",
        re.IGNORECASE
    )
)
VOLTAGE_PATTERNS = (
    re.compile(
        r"(?:архитектур\w*|систем\w*|platform|charging)(?:[^0-9]{0,20})(?P<value>\d{2,4})\s*(?:В|V|volt(?:s)?|вольт\w*)\b",
        re.IGNORECASE
    ),
    re.compile(
        r"(?P<value>\d{2,4})\s*(?:В|V|volt(?:s)?|вольт\w*)\b(?:[^0-9]{0,20})(?:архитектур\w*|систем\w*|platform|charging)",
        re.IGNORECASE
    )
)
CAMERA_PATTERNS = (
    re.compile(
        r"(?:камера|camera)(?:[^0-9]{0,20})(?P<value>\d{1,3}(?:[.,]\d+)?)\s*(?:Мп|MP)\b",
        re.IGNORECASE
    ),
    re.compile(
        r"(?P<value>\d{1,3}(?:[.,]\d+)?)\s*(?:Мп|MP)\b(?:[^0-9]{0,20})(?:камера|camera)",
        re.IGNORECASE
    )
)


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
    specs = extract_spec_highlights(item, title, summary, max_specs=max_bullets + 1)
    tags = build_hashtags(item, title)
    lines = [
        f"<b>{escape_text(publication_title)}</b>",
        "",
        f"{emoji} <b>{escape_text(title)}</b>"
    ]

    if lead:
        lines.extend(
            [
                "",
                f"<i>{escape_text(lead)}</i>"
            ]
        )

    if specs:
        lines.extend(
            [
                "",
                "<b>Характеристики:</b>"
            ]
        )
        lines.extend(f"• {escape_text(spec)}" for spec in specs)

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
        f"<b>{escape_text(publication_title)}</b>",
        "",
        f"{emoji} <b>{escape_text(title)}</b>"
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
    trimmed_specs = specs[:2]
    if trimmed_specs:
        fallback_lines.extend(
            [
                "",
                "<b>Характеристики:</b>"
            ]
        )
        fallback_lines.extend(f"• {escape_text(truncate(spec, 90))}" for spec in trimmed_specs)

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


def extract_spec_highlights(item: CandidateItem, title: str, summary: str, max_specs: int) -> list[str]:
    if max_specs <= 0 or not should_include_specs(item, title, summary):
        return []

    text = EXTRA_SPACE_RE.sub(" ", f"{title}. {summary}").strip()
    if not text:
        return []

    extractors = (
        extract_power_spec,
        extract_battery_spec,
        extract_range_spec,
        extract_acceleration_spec,
        extract_charging_spec,
        extract_torque_spec,
        extract_engine_spec,
        extract_voltage_spec,
        extract_screen_spec,
        extract_memory_spec,
        extract_camera_spec
    )

    specs: list[str] = []
    seen: set[str] = set()

    for extractor in extractors:
        spec = extractor(text)
        if not spec:
            continue
        key = spec.lower()
        if key in seen:
            continue
        seen.add(key)
        specs.append(spec)
        if len(specs) >= max_specs:
            break

    return specs


def should_include_specs(item: CandidateItem, title: str, summary: str) -> bool:
    haystack = f"{title} {summary}".lower()

    if item.topic in SPEC_FOCUS_TOPICS:
        return True

    if item.topic == "technology" and any(keyword in haystack for keyword in GADGET_KEYWORDS):
        return True

    has_model_hint = any(keyword in haystack for keyword in MODEL_KEYWORDS)
    has_gadget_hint = any(keyword in haystack for keyword in GADGET_KEYWORDS)
    has_spec_hint = any(keyword in haystack for keyword in ("характерист", "spec", "техданн"))
    return has_spec_hint and (has_model_hint or has_gadget_hint)


def extract_power_spec(text: str) -> str | None:
    for match in POWER_RE.finditer(text):
        unit = normalize_unit(match.group("unit"))
        context = context_window(text, match.start(), match.end())

        if unit == "кВт" and not re.search(r"мощност|power|output|двигател|motor|силов", context, re.IGNORECASE):
            continue
        if unit == "кВт" and re.search(r"заряд|charging|battery|батар", context, re.IGNORECASE):
            continue

        return f"Мощность: {normalize_number(match.group('value'))} {unit}"
    return None


def extract_battery_spec(text: str) -> str | None:
    match = BATTERY_RE.search(text)
    if not match:
        return None
    return f"Батарея: {normalize_number(match.group('value'))} кВт·ч"


def extract_range_spec(text: str) -> str | None:
    for pattern in RANGE_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"Запас хода: {normalize_number(match.group('value'))} км"
    return None


def extract_acceleration_spec(text: str) -> str | None:
    match = ACCELERATION_RE.search(text)
    if not match:
        return None
    return f"Разгон 0-100 км/ч: {normalize_number(match.group('value'))} с"


def extract_charging_spec(text: str) -> str | None:
    for pattern in CHARGING_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"Быстрая зарядка: до {normalize_number(match.group('value'))} кВт"
    return None


def extract_torque_spec(text: str) -> str | None:
    match = TORQUE_RE.search(text)
    if not match:
        return None
    return f"Крутящий момент: {normalize_number(match.group('value'))} Нм"


def extract_engine_spec(text: str) -> str | None:
    for pattern in ENGINE_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"Двигатель: {normalize_number(match.group('value'))} л"
    return None


def extract_voltage_spec(text: str) -> str | None:
    for pattern in VOLTAGE_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"Архитектура: {normalize_number(match.group('value'))} В"
    return None


def extract_screen_spec(text: str) -> str | None:
    for pattern in SCREEN_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"Экран: {normalize_number(match.group('value'))} дюйма"
    return None


def extract_memory_spec(text: str) -> str | None:
    for pattern in MEMORY_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"Память: {normalize_number(match.group('value'))} {normalize_unit(match.group('unit'))}"
    return None


def extract_camera_spec(text: str) -> str | None:
    for pattern in CAMERA_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"Камера: {normalize_number(match.group('value'))} Мп"
    return None


def context_window(text: str, start: int, end: int, padding: int = 28) -> str:
    left = max(0, start - padding)
    right = min(len(text), end + padding)
    return text[left:right]


def normalize_number(value: str) -> str:
    return value.strip().replace(".", ",")


def normalize_unit(value: str) -> str:
    lowered = value.strip().lower().replace(" ", "")
    mapping = {
        "л.с.": "л.с.",
        "л.с": "л.с.",
        "лс": "л.с.",
        "hp": "л.с.",
        "bhp": "л.с.",
        "kw": "кВт",
        "квт": "кВт",
        "gb": "ГБ",
        "гб": "ГБ",
        "tb": "ТБ",
        "тб": "ТБ"
    }
    return mapping.get(lowered, value.strip())


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


def detect_brand_label(item: CandidateItem, title: str = "") -> str:
    haystack = f"{title} {item.title} {item.summary} {item.source_name}".lower()

    for phrase, tag in BRAND_TAGS:
        if phrase in haystack:
            return tag

    source_tag = SOURCE_TAGS.get(item.source_group)
    if source_tag:
        return source_tag

    return item.source_name.split()[0]


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
