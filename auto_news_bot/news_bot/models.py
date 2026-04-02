from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List


@dataclass(frozen=True)
class CandidateItem:
    source_name: str
    source_group: str
    source_language: str
    source_weight: float
    title: str
    summary: str
    url: str
    image_url: str
    published_at: datetime
    topic: str
    topic_label: str
    score: float
    duplicate_count: int
    fingerprint: str
    similar_urls: List[str]
    video_url: str = ""

    @property
    def published_at_utc(self) -> datetime:
        if self.published_at.tzinfo is None:
            return self.published_at.replace(tzinfo=timezone.utc)
        return self.published_at.astimezone(timezone.utc)
