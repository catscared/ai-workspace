from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser


def _to_iso8601(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _domain_from_url(url: str | None) -> str:
    if not url:
        return "unknown"
    normalized = url.replace("https://", "").replace("http://", "")
    domain = normalized.split("/", 1)[0].strip().lower()
    return domain or "unknown"


def fetch_news_items(
    feeds: tuple[str, ...],
    max_per_feed: int = 20,
    source_type: str = "news",
    channel: str = "news",
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for feed_url in feeds:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries[:max_per_feed]:
            external_id = entry.get("id") or entry.get("link") or entry.get("title")
            if not external_id:
                continue
            content = ""
            summary = entry.get("summary")
            if summary:
                content = summary
            elif entry.get("content"):
                block = entry.get("content")[0]
                if isinstance(block, dict):
                    content = block.get("value", "")

            published = (
                _to_iso8601(entry.get("published"))
                or _to_iso8601(entry.get("updated"))
                or datetime.now(timezone.utc).isoformat()
            )
            items.append(
                {
                    "source_type": source_type,
                    "external_id": str(external_id),
                    "title": entry.get("title"),
                    "content": content,
                    "author_handle": entry.get("author"),
                    "author_followers": None,
                    "url": entry.get("link"),
                    "published_at": published,
                    "engagement": 0,
                    "metadata": {
                        "feed": feed_url,
                        "publisher_domain": _domain_from_url(entry.get("link")),
                        "channel": channel,
                    },
                }
            )
    return items
