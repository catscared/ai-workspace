from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class TelegramUpdate:
    update_id: int
    chat_id: str
    text: str
    username: str | None


class TelegramBotClient:
    def __init__(self, token: str, default_chat_id: str = "", timeout_seconds: float = 15.0) -> None:
        self.token = token.strip()
        self.default_chat_id = default_chat_id.strip()
        self.timeout_seconds = timeout_seconds
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    def send_message(self, text: str, chat_id: str | None = None) -> bool:
        if not self.enabled:
            return False
        target_chat = (chat_id or self.default_chat_id).strip()
        if not target_chat:
            return False
        payload = {"chat_id": target_chat, "text": text}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(f"{self.base_url}/sendMessage", json=payload)
            response.raise_for_status()
        return True

    def get_updates(self, offset: int | None = None, timeout: int = 10) -> list[TelegramUpdate]:
        if not self.enabled:
            return []
        params: dict[str, Any] = {"timeout": max(0, min(timeout, 50))}
        if offset is not None:
            params["offset"] = offset
        with httpx.Client(timeout=self.timeout_seconds + timeout) as client:
            response = client.get(f"{self.base_url}/getUpdates", params=params)
            response.raise_for_status()
            payload = response.json()
        updates: list[TelegramUpdate] = []
        for item in payload.get("result", []):
            update_id = int(item.get("update_id") or 0)
            message = item.get("message") or item.get("edited_message") or {}
            chat = message.get("chat") or {}
            text = str(message.get("text") or "").strip()
            chat_id = str(chat.get("id") or "")
            if not text or not chat_id:
                continue
            user = message.get("from") or {}
            updates.append(
                TelegramUpdate(
                    update_id=update_id,
                    chat_id=chat_id,
                    text=text,
                    username=user.get("username"),
                )
            )
        return updates
