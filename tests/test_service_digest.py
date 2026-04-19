from __future__ import annotations

import tempfile
from pathlib import Path

from hot_monitor.config import Settings
from hot_monitor.database import Database
from hot_monitor.service import HotMonitorService


def test_build_hotspot_digest_includes_title_insight_and_link() -> None:
    db_path = Path(tempfile.gettempdir()) / "hot_monitor_test_digest.db"
    settings = Settings(database_path=str(db_path), telegram_hotspot_push_limit=2)
    service = HotMonitorService(db=Database(settings.database_path), settings=settings)
    message = service._build_hotspot_digest(
        hotspots=[
            {
                "title": "Test signal",
                "url": "https://example.com/signal",
                "confidence": 0.91,
                "score": 9.1,
                "title_zh": "测试中文标题",
                "title_en": "Test English Title",
                "insight_zh": "这是中文深度观点",
                "insight_en": "This is an English deep insight",
            }
        ],
    )
    assert "标题: 测试中文标题" in message
    assert "Title: Test English Title" in message
    assert "AI观点(中文): 这是中文深度观点" in message
    assert "AI Insight(EN): This is an English deep insight" in message
    assert "Link: https://example.com/signal" in message
