from __future__ import annotations

import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

from news_bot.config import AppConfig


class TelegramPublisher:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def publish(self, message: str, image_url: str = "", caption: str = "") -> None:
        if image_url:
            try:
                self._publish_photo(image_url, caption or message)
                return
            except RuntimeError as error:
                print(f"[telegram] photo upload failed, fallback to text: {error}", file=sys.stderr)

        self._publish_message(message)

    def _publish_message(self, message: str) -> None:
        payload = urllib.parse.urlencode(
            {
                "chat_id": self.config.telegram.channel_id,
                "text": message,
                "disable_web_page_preview": "true" if self.config.telegram.disable_web_page_preview else "false"
            }
        ).encode("utf-8")
        endpoint = f"https://api.telegram.org/bot{self.config.telegram.bot_token}/sendMessage"
        request = urllib.request.Request(
            endpoint,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": self.config.user_agent
            },
            method="POST"
        )

        raw = self._send_request(request)
        payload = json.loads(raw.decode("utf-8"))
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram API rejected message: {payload}")

    def _publish_photo(self, image_url: str, caption: str) -> None:
        image_bytes, file_name, content_type = self._download_image(image_url)
        boundary = f"----AutoNewsBot{uuid.uuid4().hex}"
        body = self._build_multipart_body(
            boundary=boundary,
            fields={
                "chat_id": self.config.telegram.channel_id,
                "caption": caption
            },
            file_field_name="photo",
            file_name=file_name,
            file_content=image_bytes,
            file_content_type=content_type
        )

        endpoint = f"https://api.telegram.org/bot{self.config.telegram.bot_token}/sendPhoto"
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": self.config.user_agent
            },
            method="POST"
        )

        raw = self._send_request(request)
        payload = json.loads(raw.decode("utf-8"))
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram API rejected photo: {payload}")

    def _download_image(self, image_url: str) -> tuple[bytes, str, str]:
        request = urllib.request.Request(
            image_url,
            headers={
                "User-Agent": self.config.user_agent,
                "Accept": "image/*,*/*;q=0.8"
            }
        )

        try:
            with urllib.request.urlopen(request, timeout=self.config.request_timeout_seconds) as response:
                content_type = response.info().get_content_type()
                image_bytes = response.read()
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Image HTTP {error.code}: {details}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Image connection error: {error.reason}") from error

        if not content_type.startswith("image/"):
            guessed_type = mimetypes.guess_type(image_url)[0] or ""
            content_type = guessed_type or content_type

        if not content_type.startswith("image/"):
            raise RuntimeError(f"Unsupported image content type: {content_type}")

        parsed = urllib.parse.urlsplit(image_url)
        file_name = os.path.basename(parsed.path) or "news-image"
        return image_bytes, file_name, content_type

    def _build_multipart_body(
        self,
        boundary: str,
        fields: dict[str, str],
        file_field_name: str,
        file_name: str,
        file_content: bytes,
        file_content_type: str
    ) -> bytes:
        buffer = bytearray()
        line_break = b"\r\n"

        for name, value in fields.items():
            buffer.extend(f"--{boundary}".encode("utf-8"))
            buffer.extend(line_break)
            buffer.extend(f'Content-Disposition: form-data; name="{name}"'.encode("utf-8"))
            buffer.extend(line_break)
            buffer.extend(line_break)
            buffer.extend(value.encode("utf-8"))
            buffer.extend(line_break)

        buffer.extend(f"--{boundary}".encode("utf-8"))
        buffer.extend(line_break)
        buffer.extend(
            f'Content-Disposition: form-data; name="{file_field_name}"; filename="{file_name}"'.encode("utf-8")
        )
        buffer.extend(line_break)
        buffer.extend(f"Content-Type: {file_content_type}".encode("utf-8"))
        buffer.extend(line_break)
        buffer.extend(line_break)
        buffer.extend(file_content)
        buffer.extend(line_break)
        buffer.extend(f"--{boundary}--".encode("utf-8"))
        buffer.extend(line_break)
        return bytes(buffer)

    def _send_request(self, request: urllib.request.Request) -> bytes:
        try:
            with urllib.request.urlopen(request, timeout=self.config.request_timeout_seconds) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Telegram API HTTP {error.code}: {details}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Telegram API connection error: {error.reason}") from error
