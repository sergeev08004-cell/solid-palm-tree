from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request

from news_bot.config import AppConfig


META_IMAGE_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image|twitter:image:src)["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE
)
IMG_SRC_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)
NOISY_IMAGE_RE = re.compile(r"(logo|icon|sprite|avatar|favicon|banner-ad|analytics)", re.IGNORECASE)

def fetch_page_images(url: str, config: AppConfig, limit: int = 4) -> list[str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": config.user_agent,
            "Accept": "text/html,application/xhtml+xml"
        }
    )
    with urllib.request.urlopen(request, timeout=config.request_timeout_seconds) as response:
        content_type = response.info().get_content_type()
        payload = response.read(512_000)

    if "html" not in content_type:
        return []

    page = payload.decode("utf-8", errors="ignore")
    candidates = []

    for match in META_IMAGE_RE.findall(page):
        candidates.append(absolute_url(match, url))

    for match in IMG_SRC_RE.findall(page):
        candidates.append(absolute_url(match, url))

    return unique_images(candidates, limit=limit)


def fetch_page_image(url: str, config: AppConfig) -> str:
    images = fetch_page_images(url, config, limit=1)
    return images[0] if images else ""


def absolute_url(value: str, base_url: str) -> str:
    clean_value = html.unescape(value.strip())
    return urllib.parse.urljoin(base_url, clean_value)


def unique_images(candidates: list[str], limit: int) -> list[str]:
    seen = set()
    images = []

    for candidate in candidates:
        clean = candidate.strip()
        if not clean or clean.startswith("data:"):
            continue
        if NOISY_IMAGE_RE.search(clean):
            continue
        if clean in seen:
            continue
        seen.add(clean)
        images.append(clean)
        if len(images) >= limit:
            break

    return images
