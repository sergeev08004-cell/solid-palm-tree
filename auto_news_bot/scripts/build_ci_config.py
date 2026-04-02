#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build GitHub Actions config for Auto News Bot")
    parser.add_argument("--base", default="config.example.json", help="Base config JSON")
    parser.add_argument("--output", default="config.ci.json", help="Output config JSON")
    return parser.parse_args()


def getenv_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> int:
    args = parse_args()
    base_path = Path(args.base).resolve()
    output_path = Path(args.output).resolve()

    payload = json.loads(base_path.read_text(encoding="utf-8"))

    bot_token = getenv_required("TELEGRAM_BOT_TOKEN")
    channel_id = getenv_required("TELEGRAM_CHANNEL_ID")
    publication_title = os.environ.get("AUTO_NEWS_PUBLICATION_TITLE", "").strip()
    if channel_id.startswith("@"):
        user_agent = f"AutoNewsBot/1.0 (+https://t.me/{channel_id.lstrip('@')})"
    else:
        user_agent = "AutoNewsBot/1.0 (+https://github.com/actions)"

    payload["telegram"]["bot_token"] = bot_token
    payload["telegram"]["channel_id"] = channel_id
    payload["database_path"] = "state/news.db"
    payload["publication_title"] = publication_title
    payload["user_agent"] = user_agent

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
