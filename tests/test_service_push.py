from __future__ import annotations

import tempfile
from pathlib import Path

from hot_monitor.config import Settings
from hot_monitor.database import Database
from hot_monitor.service import HotMonitorService


class _TelegramStub:
    def __init__(self, fail_markdown: bool = False) -> None:
        self.fail_markdown = fail_markdown
        self.calls: list[tuple[str, str | None]] = []

    def send_message(self, text: str, chat_id: str | None = None, parse_mode: str | None = None) -> bool:
        self.calls.append((text, parse_mode))
        if self.fail_markdown and parse_mode == "MarkdownV2":
            raise RuntimeError("markdown failed")
        return True


def test_notify_collect_result_fallback_plaintext() -> None:
    db_path = Path(tempfile.gettempdir()) / "hot_monitor_test_push.db"
    settings = Settings(database_path=str(db_path))
    service = HotMonitorService(db=Database(settings.database_path), settings=settings)
    service.telegram = _TelegramStub(fail_markdown=True)  # type: ignore[assignment]

    success, note = service._notify_collect_result("1\\) 标题: [X](https://example.com)")
    assert success is True
    assert "fallback_plaintext_after_markdown_error" in note


def test_notify_collect_result_markdown_success() -> None:
    db_path = Path(tempfile.gettempdir()) / "hot_monitor_test_push_ok.db"
    settings = Settings(database_path=str(db_path))
    service = HotMonitorService(db=Database(settings.database_path), settings=settings)
    stub = _TelegramStub(fail_markdown=False)
    service.telegram = stub  # type: ignore[assignment]

    success, note = service._notify_collect_result("ok")
    assert success is True
    assert note == "markdown"
    assert stub.calls[0][1] == "MarkdownV2"
