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


def fetch_page_image(url: str, config: AppConfig) -> str:
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
        return ""

    page = payload.decode("utf-8", errors="ignore")

    meta_match = META_IMAGE_RE.search(page)
    if meta_match:
        return absolute_url(meta_match.group(1), url)

    image_match = IMG_SRC_RE.search(page)
    if image_match:
        return absolute_url(image_match.group(1), url)

    return ""


def absolute_url(value: str, base_url: str) -> str:
    clean_value = html.unescape(value.strip())
    return urllib.parse.urljoin(base_url, clean_value)
