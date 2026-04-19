from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI Blockchain Hotspot Monitor"
    database_path: str = os.getenv("DATABASE_PATH", "/workspace/data/hot_monitor.db")
    x_bearer_token: str = os.getenv("X_BEARER_TOKEN", "")
    x_max_results: int = int(os.getenv("X_MAX_RESULTS", "20"))
    kol_min_followers: int = int(os.getenv("KOL_MIN_FOLLOWERS", "200000"))
    collection_cron: str = os.getenv("COLLECTION_CRON", "0 8 * * *")
    collection_interval_minutes: int = int(os.getenv("COLLECTION_INTERVAL_MINUTES", "0"))
    news_rss_feeds: tuple[str, ...] = tuple(
        feed.strip()
        for feed in os.getenv(
            "NEWS_RSS_FEEDS",
            ",".join(
                [
                    "https://www.coindesk.com/arc/outboundfeeds/rss/",
                    "https://cointelegraph.com/rss",
                    "https://decrypt.co/feed",
                ]
            ),
        ).split(",")
        if feed.strip()
    )


settings = Settings()
