from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, List, Tuple

from news_bot.models import CandidateItem
from news_bot.storage import Storage
from news_bot.text_tools import normalize_url

if TYPE_CHECKING:
    from news_bot.worker import CollectedItem


TOPIC_RULES = {
    "recalls": {
        "label": "Отзывная кампания",
        "weight": 3.8,
        "keywords": ["отзыв", "recall", "service action", "дефект", "неисправн", "кампания"]
    },
    "law": {
        "label": "Регулирование",
        "weight": 3.5,
        "keywords": ["закон", "штраф", "пдд", "осаго", "налог", "регулятор", "government", "rule"]
    },
    "new_models": {
        "label": "Новая модель",
        "weight": 3.2,
        "keywords": ["представ", "дебют", "новый", "launch", "debut", "unveil", "reveals", "arrives"]
    },
    "prices": {
        "label": "Цены",
        "weight": 2.8,
        "keywords": ["цена", "стоимост", "price", "pricing", "costs", "$"]
    },
    "sales": {
        "label": "Продажи",
        "weight": 2.7,
        "keywords": ["продаж", "sales", "рынок", "market", "спрос", "dealer"]
    },
    "production": {
        "label": "Производство",
        "weight": 2.9,
        "keywords": ["завод", "производ", "assembly", "factory", "plant", "manufactur"]
    },
    "electric": {
        "label": "Электромобили",
        "weight": 2.6,
        "keywords": ["ev", "electric", "электро", "battery", "charging", "зарядк"]
    },
    "technology": {
        "label": "Технологии",
        "weight": 2.3,
        "keywords": ["software", "ai", "автопилот", "tech", "technology", "платформ", "chip"]
    }
}
DEFAULT_TOPIC = ("industry", "Отрасль", 1.7)


def rank_candidates(
    items: List[CollectedItem],
    storage: Storage,
    priority_topics: List[str],
    max_age_hours: int,
    min_age_minutes: int
) -> List[CandidateItem]:
    now = datetime.now(timezone.utc)
    fresh_after = now - timedelta(hours=max_age_hours)
    mature_before = now - timedelta(minutes=min_age_minutes)

    filtered = [
        item for item in items
        if fresh_after <= item.published_at <= mature_before
        and not storage.was_published(item.fingerprint)
    ]

    deduplicated = deduplicate(filtered)
    ranked = []
    topic_bonus = {topic: (len(priority_topics) - index) * 0.25 for index, topic in enumerate(priority_topics)}

    for group in deduplicated:
        best = max(group, key=lambda candidate: candidate.source_weight)
        topic, label, topic_weight = detect_topic(f"{best.title} {best.summary}")
        age_hours = max((now - best.published_at).total_seconds() / 3600, 0.0)
        freshness = max(0.0, 3.0 - math.log1p(age_hours))
        duplicates_bonus = 0.45 * (len(group) - 1)
        score = topic_weight + freshness + best.source_weight + duplicates_bonus + topic_bonus.get(topic, 0.0)

        ranked.append(
            CandidateItem(
                source_name=best.source_name,
                source_language=best.source_language,
                source_weight=best.source_weight,
                title=best.title,
                summary=best.summary,
                url=best.url,
                image_url=best.image_url,
                published_at=best.published_at,
                topic=topic,
                topic_label=label,
                score=round(score, 3),
                duplicate_count=len(group),
                fingerprint=best.fingerprint,
                similar_urls=[item.url for item in group]
            )
        )

    ranked.sort(key=lambda item: (item.score, item.published_at), reverse=True)
    return ranked


def deduplicate(items: List[CollectedItem]) -> List[List[CollectedItem]]:
    groups: List[List[CollectedItem]] = []

    for item in items:
        matched_group = None
        for group in groups:
            if any(is_same_story(item, existing) for existing in group):
                matched_group = group
                break

        if matched_group is None:
            groups.append([item])
        else:
            matched_group.append(item)

    return groups


def is_same_story(left: CollectedItem, right: CollectedItem) -> bool:
    if normalize_url(left.url) == normalize_url(right.url):
        return True

    similarity = SequenceMatcher(None, left.title_key, right.title_key).ratio()
    shared_tokens = len(set(left.tokens) & set(right.tokens))
    return similarity >= 0.92 or (similarity >= 0.82 and shared_tokens >= 4)


def detect_topic(text: str) -> Tuple[str, str, float]:
    lowered = text.lower()

    for topic, rule in TOPIC_RULES.items():
        if any(keyword in lowered for keyword in rule["keywords"]):
            return topic, rule["label"], float(rule["weight"])

    return DEFAULT_TOPIC
