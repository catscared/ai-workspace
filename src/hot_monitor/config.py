from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _to_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return tuple()
    return tuple(part.strip() for part in value.split(",") if part.strip())


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
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    telegram_poll_interval_seconds: int = int(os.getenv("TELEGRAM_POLL_INTERVAL_SECONDS", "20"))
    telegram_notify_on_collect: bool = _to_bool(os.getenv("TELEGRAM_NOTIFY_ON_COLLECT"), True)

    llm_api_base_url: str = os.getenv("LLM_API_BASE_URL", "https://api.openai.com/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))

    dune_api_key: str = os.getenv("DUNE_API_KEY", "")
    dune_query_ids: tuple[str, ...] = _to_csv(os.getenv("DUNE_QUERY_IDS"))
    defillama_enabled: bool = _to_bool(os.getenv("DEFILLAMA_ENABLED"), True)
    github_release_repos: tuple[str, ...] = _to_csv(os.getenv("GITHUB_RELEASE_REPOS"))
    github_token: str = os.getenv("GITHUB_TOKEN", "")


settings = Settings()
