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
                "event_zh": "这是中文事件要点",
                "insight_zh": "这是中文深度观点",
                "channel": "news",
            }
        ],
    )
    assert "标题: [Test signal](https://example\\.com/signal)" in message
    assert "事件要点（中文解读）:\n这是中文事件要点" in message
    assert "AI深度观点:\n这是中文深度观点" in message


def test_build_hotspot_digest_groups_by_channel() -> None:
    db_path = Path(tempfile.gettempdir()) / "hot_monitor_test_digest_group.db"
    settings = Settings(database_path=str(db_path), telegram_hotspot_push_limit=2)
    service = HotMonitorService(db=Database(settings.database_path), settings=settings)
    message = service._build_hotspot_digest(
        hotspots=[
            {
                "title": "KOL Tweet",
                "url": "https://x.com/abc/status/1",
                "confidence": 0.8,
                "score": 8.0,
                "event_zh": "KOL 事件要点",
                "insight_zh": "KOL insight",
                "channel": "x_kol",
            },
            {
                "title": "News article",
                "url": "https://news.example.com/1",
                "confidence": 0.7,
                "score": 7.0,
                "event_zh": "News 事件要点",
                "insight_zh": "News insight",
                "channel": "news",
            },
        ]
    )
    assert "【权威区块链媒体】" in message
    assert "【X 大V/KOL 动态】" in message
