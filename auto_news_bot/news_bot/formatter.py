from __future__ import annotations

import html
import re
from datetime import timezone
from urllib.parse import urlsplit

from news_bot.models import CandidateItem


MULTI_PUNCTUATION_RE = re.compile(r"[!?]+")
EXTRA_SPACE_RE = re.compile(r"\s+")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
HASHTAG_CLEAN_RE = re.compile(r"[^0-9A-Za-zА-Яа-яЁё]+")
PRICE_VALUE_RE = re.compile(
    r"((?:от|from)?\s*(?:[$€£¥₽₸]\s?\d[\d\s.,]*(?:\s?(?:k|m))?|\d[\d\s.,]*(?:\s?(?:тыс\.?|млн|k|m|million))?\s*"
    r"(?:руб(?:лей|ля|\.?)|₽|usd|доллар(?:ов|а)?|eur|евро|€|£|фунт(?:ов|а)?|тенге|₸|yuan|юан(?:ей|я)?|¥)))",
    re.IGNORECASE
)
SUMMARY_SPLIT_RE = re.compile(
    r"(?<=[.!?])\s+|(?<=[а-яё0-9])\s+(?=(?:В|На|По|Для|Однако|Также|Компания|В компании|Новинку|Новый|Это|При этом)\b)"
)
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
    "gadgets": "🧭",
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
    "gadgets": "Автогаджеты",
    "technology": "Технологии",
    "industry": "Автоновости"
}
GADGET_HASHTAG_RULES = (
    ("carplay", "CarPlay"),
    ("android auto", "AndroidAuto"),
    ("dash cam", "Видеорегистраторы"),
    ("dashcam", "Видеорегистраторы"),
    ("видеорегистратор", "Видеорегистраторы"),
    ("navigator", "Навигаторы"),
    ("navigation", "Навигация"),
    ("навигатор", "Навигаторы"),
    ("head unit", "Мультимедиа"),
    ("infotainment", "Мультимедиа"),
    ("мультимедиа", "Мультимедиа"),
    ("магнитол", "Мультимедиа"),
    ("charger", "Зарядка"),
    ("charging pad", "Зарядка"),
    ("зарядн", "Зарядка"),
    ("screen", "Дисплеи"),
    ("display", "Дисплеи"),
    ("экран", "Дисплеи"),
    ("диспле", "Дисплеи"),
    ("camera", "Автокамеры"),
    ("камера", "Автокамеры")
)
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
    ("garmin", "Garmin"),
    ("tomtom", "TomTom"),
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
    "garmin": "Garmin",
    "drom": "Drom",
    "motorru": "MotorRu"
}
SPEC_FOCUS_TOPICS = {"new_models", "electric", "gadgets"}
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
PRICE_PATTERNS = (
    re.compile(
        r"(?:цен\w*|стоимост\w*|price(?:d)?|pricing|starts?\s+at|starting\s+at|from)(?:[^0-9$€£¥₽₸]{0,18})"
        r"(?P<value>(?:от|from)?\s*(?:[$€£¥₽₸]\s?\d[\d\s.,]*(?:\s?(?:k|m))?|\d[\d\s.,]*(?:\s?(?:тыс\.?|млн|k|m|million))?\s*"
        r"(?:руб(?:лей|ля|\.?)|₽|usd|доллар(?:ов|а)?|eur|евро|€|£|фунт(?:ов|а)?|тенге|₸|yuan|юан(?:ей|я)?|¥)))",
        re.IGNORECASE
    ),
)
MODEL_STOPWORDS = {
    "обновила",
    "обновил",
    "представила",
    "представил",
    "показала",
    "показал",
    "раскрыла",
    "раскрыл",
    "сообщила",
    "сообщил",
    "запустила",
    "запустил",
    "получила",
    "получил",
    "получили",
    "получит",
    "получат",
    "вышла",
    "вышел",
    "вышли",
    "объявила",
    "объявил",
    "стартовали",
    "начались",
    "стартовал",
    "получает",
    "получают",
    "to",
    "for",
    "gets",
    "get",
    "gains",
    "gain",
    "debuts",
    "debuts,"
}
MODEL_BRAND_PATTERN = "|".join(
    sorted((re.escape(phrase) for phrase, _ in BRAND_TAGS), key=len, reverse=True)
)
MODEL_MENTION_RE = re.compile(
    rf"\b(?P<brand>{MODEL_BRAND_PATTERN})(?P<tail>(?:\s+[A-Za-zА-Яа-я0-9][A-Za-zА-Яа-я0-9+/.\-]*){{1,4}})",
    re.IGNORECASE
)


def format_post(item: CandidateItem, channel_id: str = "") -> str:
    return _format_post(
        item,
        channel_id=channel_id,
        summary_limit=520,
        max_length=4096,
        max_bullets=3,
        include_spoiler=True
    )


def format_caption(item: CandidateItem, channel_id: str = "") -> str:
    return _format_post(
        item,
        channel_id=channel_id,
        summary_limit=280,
        max_length=1024,
        max_bullets=2,
        include_spoiler=False
    )


def _format_post(
    item: CandidateItem,
    channel_id: str,
    summary_limit: int,
    max_length: int,
    max_bullets: int,
    include_spoiler: bool
) -> str:
    title = neutralize_headline(item.title)
    summary = truncate(neutralize_text(item.summary), summary_limit)
    paragraphs = build_reference_paragraphs(item, title, summary, max_paragraphs=max_bullets + 1)
    price_block = build_price_block(item, title, summary, max_lines=max_bullets)
    cta_line = build_channel_cta(channel_id)
    tags = build_hashtags(item, title)
    lines = [f"<b>{escape_text(title)}</b>"]

    for paragraph in paragraphs[:max(1, max_bullets + 1)]:
        lines.extend(["", emphasize_paragraph(paragraph)])

    if price_block:
        price_lines = price_block[1:] if len(price_block) > 1 else [price_block[0].split(": ", 1)[-1]]
        if price_lines:
            lines.extend(["", emphasize_paragraph(f"Цена: {price_lines[0]}")])

    if item.duplicate_count > 1:
        lines.extend(["", f"<b>Сюжет подтвержден {item.duplicate_count} источниками.</b>"])

    if cta_line:
        lines.extend(["", cta_line])

    if tags:
        lines.extend(["", " ".join(f"#{tag}" for tag in tags[:4])])

    text = "\n".join(lines).strip()
    if len(text) <= max_length:
        return text

    fallback_lines = [f"<b>{escape_text(title)}</b>"]
    for paragraph in paragraphs[:max(1, max_bullets)]:
        fallback_lines.extend(["", emphasize_paragraph(truncate(paragraph, 190))])
    if price_block:
        price_lines = price_block[1:] if len(price_block) > 1 else [price_block[0].split(": ", 1)[-1]]
        if price_lines:
            fallback_lines.extend(["", emphasize_paragraph(truncate(f"Цена: {price_lines[0]}", 110))])
    if cta_line:
        fallback_lines.extend(["", cta_line])
    if tags:
        fallback_lines.extend(["", " ".join(f"#{tag}" for tag in tags[:3])])

    return truncate("\n".join(fallback_lines).strip(), max_length)


def build_reference_paragraphs(item: CandidateItem, title: str, summary: str, max_paragraphs: int) -> list[str]:
    paragraphs: list[str] = []
    model_specs = extract_model_spec_lines(item, title, summary, max_models=2)
    specs = [] if model_specs else extract_spec_highlights(item, title, summary, max_specs=3)

    if model_specs:
        paragraphs.extend(model_specs[:2])
    elif specs:
        paragraphs.append(", ".join(specs[:3]))

    if summary:
        paragraphs.extend(group_story_sentences(summary, max_paragraphs=max_paragraphs))

    unique: list[str] = []
    seen: set[str] = set()
    title_key = title.lower().strip(" .")
    for paragraph in paragraphs:
        clean = paragraph.strip()
        if not clean:
            continue
        if clean.lower().strip(" .") == title_key:
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(clean)
        if len(unique) >= max_paragraphs:
            break

    if not unique:
        unique.append("Новый материал по автомобильной теме уже появился в ленте канала.")

    return unique


def group_story_sentences(summary: str, max_paragraphs: int) -> list[str]:
    sentences = [neutralize_text(part) for part in SUMMARY_SPLIT_RE.split(summary) if part.strip()]
    if not sentences:
        return []

    paragraphs: list[str] = []
    current: list[str] = []
    for sentence in sentences:
        if current and (len(" ".join(current + [sentence])) > 220 or len(current) >= 2):
            paragraphs.append(" ".join(current))
            current = [sentence]
        else:
            current.append(sentence)
        if len(paragraphs) >= max_paragraphs:
            break

    if current and len(paragraphs) < max_paragraphs:
        paragraphs.append(" ".join(current))

    return paragraphs[:max_paragraphs]


def emphasize_paragraph(text: str) -> str:
    escaped = escape_text(text)
    escaped = PRICE_VALUE_RE.sub(r"<b>\1</b>", escaped)
    for phrase in (
        "автопилот",
        "быстрая зарядка",
        "адаптивная подвеска",
        "полный привод",
        "мультимедиа",
        "экосистема",
        "carplay",
        "android auto",
        "запас хода",
    ):
        escaped = re.sub(
            rf"\b({re.escape(phrase)})\b",
            r"<b>\1</b>",
            escaped,
            flags=re.IGNORECASE
        )
    return escaped


def build_channel_cta(channel_id: str) -> str:
    if not channel_id.startswith("@"):
        return ""
    handle = channel_id.lstrip("@")
    return f"👉 <a href=\"https://t.me/{escape_attr(handle)}\">{escape_text(channel_id)}. Подписаться</a>"


def build_story_blocks(summary: str, max_bullets: int, skip_model_sentences: bool = False) -> tuple[str, list[str]]:
    if not summary:
        return "", []

    sentences = [neutralize_text(part) for part in SENTENCE_SPLIT_RE.split(summary) if part.strip()]
    if not sentences:
        clean_summary = neutralize_text(summary)
        return clean_summary, []

    lead = truncate(sentences[0], 190)
    if skip_model_sentences and sentence_is_model_heavy(sentences[0]):
        lead = ""
    bullets: list[str] = []

    for sentence in sentences[1:]:
        if skip_model_sentences and (
            sentence_is_model_heavy(sentence) or extract_specs_from_text(sentence, max_specs=1)
        ):
            continue
        if extract_price_value(sentence):
            continue
        bullet = truncate(strip_leading_connector(sentence), 140)
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


def extract_model_spec_lines(item: CandidateItem, title: str, summary: str, max_models: int) -> list[str]:
    if max_models <= 0 or not should_include_specs(item, title, summary):
        return []

    text = EXTRA_SPACE_RE.sub(" ", summary or title).strip()
    mentions = extract_model_mentions(text)
    if len(mentions) < 2:
        return []

    grouped: dict[str, list[str]] = {}
    ordered_models: list[str] = []

    for index, (model_name, start, end) in enumerate(mentions):
        segment_end = mentions[index + 1][1] if index + 1 < len(mentions) else len(text)
        segment = text[start:segment_end]
        specs = extract_specs_from_text(segment, max_specs=3)
        if not specs:
            continue
        if model_name not in grouped:
            grouped[model_name] = []
            ordered_models.append(model_name)
        for spec in specs:
            if spec not in grouped[model_name]:
                grouped[model_name].append(spec)

    lines = [
        f"{model_name}: {', '.join(grouped[model_name][:3])}"
        for model_name in ordered_models
        if grouped.get(model_name)
    ]
    if len(lines) < 2:
        return []
    return lines[:max_models]


def extract_spec_highlights(item: CandidateItem, title: str, summary: str, max_specs: int) -> list[str]:
    if max_specs <= 0 or not should_include_specs(item, title, summary):
        return []

    text = EXTRA_SPACE_RE.sub(" ", f"{title}. {summary}").strip()
    if not text:
        return []

    return extract_specs_from_text(text, max_specs=max_specs)


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


def extract_specs_from_text(text: str, max_specs: int) -> list[str]:
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


def extract_model_mentions(text: str) -> list[tuple[str, int, int]]:
    mentions: list[tuple[str, int, int]] = []
    seen: set[str] = set()

    for match in MODEL_MENTION_RE.finditer(text):
        brand = match.group("brand").strip()
        tail_tokens = [clean_token(token) for token in match.group("tail").split()]
        model_tokens: list[str] = []

        for token in tail_tokens:
            if not is_model_token(token):
                break
            model_tokens.append(token)

        if not model_tokens:
            continue

        model_name = " ".join([brand] + model_tokens)
        key = model_name.lower()
        if key in seen:
            continue
        seen.add(key)
        mentions.append((model_name, match.start(), match.end()))

    return mentions


def is_model_token(token: str) -> bool:
    cleaned = clean_token(token)
    if not cleaned:
        return False
    if cleaned.lower() in MODEL_STOPWORDS:
        return False
    if any(char.isdigit() for char in cleaned):
        return True
    if cleaned != cleaned.lower():
        return True
    return False


def clean_token(token: str) -> str:
    return token.strip(" ,.;:()[]{}<>\"'")


def sentence_is_model_heavy(text: str) -> bool:
    cleaned = strip_leading_connector(text)
    return bool(
        len(extract_model_mentions(cleaned)) >= 2
        or (
            extract_model_mentions(cleaned)
            and (extract_specs_from_text(cleaned, max_specs=1) or extract_price_value(cleaned))
        )
    )


def strip_leading_connector(text: str) -> str:
    return re.sub(r"^(?:и|а|но|also|and)\s+", "", text.strip(), flags=re.IGNORECASE)


def build_price_block(item: CandidateItem, title: str, summary: str, max_lines: int) -> list[str]:
    text = EXTRA_SPACE_RE.sub(" ", f"{title}. {summary}").strip()
    if not text:
        return []

    model_prices = extract_model_price_lines(item, title, summary, max_lines=max_lines)
    if len(model_prices) > 1:
        return ["💰 <b>Цены:</b>", *model_prices[:max_lines]]

    if model_prices:
        return [f"💰 <b>Цена:</b> {model_prices[0].split(': ', 1)[-1]}"]

    price_value = extract_price_value(text)
    if not price_value:
        return []
    return [f"💰 <b>Цена:</b> {price_value}"]


def extract_model_price_lines(item: CandidateItem, title: str, summary: str, max_lines: int) -> list[str]:
    if max_lines <= 0 or not should_include_specs(item, title, summary):
        return []

    text = EXTRA_SPACE_RE.sub(" ", summary or title).strip()
    mentions = extract_model_mentions(text)
    if len(mentions) < 2:
        return []

    lines: list[str] = []
    for index, (model_name, start, end) in enumerate(mentions):
        segment_end = mentions[index + 1][1] if index + 1 < len(mentions) else len(text)
        segment = text[start:segment_end]
        price_value = extract_price_value(segment)
        if not price_value:
            continue
        lines.append(f"{model_name}: {price_value}")
        if len(lines) >= max_lines:
            break
    return lines


def extract_price_value(text: str) -> str | None:
    for pattern in PRICE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        value = EXTRA_SPACE_RE.sub(" ", match.group("value")).strip(" .,:;")
        lowered = value.lower()
        if lowered.startswith("from "):
            value = f"от {value[5:]}"
        return value
    return None


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

    model_tag = extract_model_hashtag(f"{title}. {item.summary}")
    if model_tag and model_tag not in tags:
        tags.append(model_tag)

    gadget_tag = detect_gadget_hashtag(haystack)
    if gadget_tag and gadget_tag not in tags:
        tags.append(gadget_tag)

    topic_tag = TOPIC_HASHTAGS.get(item.topic, "Автоновости")
    if topic_tag not in tags:
        tags.append(topic_tag)

    source_tag = SOURCE_TAGS.get(item.source_group)
    if source_tag and source_tag not in tags:
        tags.append(source_tag)

    if "Автоновости" not in tags and len(tags) < 4:
        tags.append("Автоновости")

    return tags[:4]


def extract_model_hashtag(text: str) -> str:
    mentions = extract_model_mentions(text)
    if not mentions:
        return ""

    return sanitize_hashtag(mentions[0][0])


def detect_gadget_hashtag(haystack: str) -> str:
    for keyword, tag in GADGET_HASHTAG_RULES:
        if keyword in haystack:
            return tag
    return ""


def sanitize_hashtag(value: str, max_length: int = 32) -> str:
    cleaned = HASHTAG_CLEAN_RE.sub("", value)
    cleaned = cleaned[:max_length]
    if not cleaned:
        return ""
    if not any(char.isalpha() for char in cleaned):
        return ""
    return cleaned


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
