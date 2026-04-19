from __future__ import annotations

import tempfile
from pathlib import Path

from hot_monitor.config import Settings
from hot_monitor.database import Database
from hot_monitor.service import HotMonitorService


def test_signal_tier_boundaries() -> None:
    assert HotMonitorService._signal_tier(0.9) == ("HIGH", "高")
    assert HotMonitorService._signal_tier(0.8) == ("HIGH", "高")
    assert HotMonitorService._signal_tier(0.79) == ("MEDIUM", "中")
    assert HotMonitorService._signal_tier(0.55) == ("MEDIUM", "中")
    assert HotMonitorService._signal_tier(0.2) == ("LOW", "低")


def test_build_hotspot_digest_includes_evidence_and_bilingual() -> None:
    db_path = Path(tempfile.gettempdir()) / "hot_monitor_test_digest.db"
    settings = Settings(database_path=str(db_path), telegram_hotspot_push_limit=2)
    service = HotMonitorService(db=Database(settings.database_path), settings=settings)
    message = service._build_hotspot_digest(
        result={"inserted_raw_items": 3, "hotspots_detected": 2, "monitor_events_detected": 1},
        hotspots=[
            {
                "title": "Test signal",
                "source_type": "news",
                "url": "https://example.com/signal",
                "category": "ai-blockchain-adoption",
                "confidence": 0.91,
                "score": 9.1,
                "summary_zh": "中文摘要",
                "summary_en": "English summary",
            }
        ],
    )
    assert "HIGH/高" in message
    assert "Evidence: https://example.com/signal" in message
    assert "ZH: 中文摘要" in message
    assert "EN: English summary" in message
