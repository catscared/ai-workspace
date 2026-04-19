from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx


class XClient:
    def __init__(self, bearer_token: str, timeout_seconds: float = 15.0) -> None:
        self.bearer_token = bearer_token.strip()
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://api.x.com/2"

    @property
    def enabled(self) -> bool:
        return bool(self.bearer_token)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.bearer_token}"}

    def search_recent_posts(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        params = {
            "query": query,
            "max_results": max(10, min(max_results, 100)),
            "tweet.fields": "created_at,author_id,public_metrics,lang",
            "user.fields": "name,username,public_metrics,verified",
            "expansions": "author_id",
        }
        url = f"{self.base_url}/tweets/search/recent"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(url, headers=self._headers(), params=params)
            response.raise_for_status()
            payload = response.json()

        users_map: dict[str, dict[str, Any]] = {}
        includes = payload.get("includes") or {}
        for user in includes.get("users", []):
            users_map[user.get("id", "")] = user

        items: list[dict[str, Any]] = []
        for tweet in payload.get("data", []):
            author = users_map.get(tweet.get("author_id", ""), {})
            public_metrics = tweet.get("public_metrics") or {}
            followers = int((author.get("public_metrics") or {}).get("followers_count") or 0)
            engagement = int(
                (public_metrics.get("retweet_count") or 0)
                + (public_metrics.get("reply_count") or 0)
                + (public_metrics.get("like_count") or 0)
                + (public_metrics.get("quote_count") or 0)
            )
            tweet_id = tweet.get("id")
            if not tweet_id:
                continue
            items.append(
                {
                    "source_type": "x",
                    "external_id": str(tweet_id),
                    "title": None,
                    "content": tweet.get("text", ""),
                    "author_handle": author.get("username"),
                    "author_followers": followers,
                    "url": f"https://x.com/{author.get('username', 'i')}/status/{tweet_id}",
                    "published_at": tweet.get("created_at")
                    or datetime.now(timezone.utc).isoformat(),
                    "engagement": engagement,
                    "metadata": {
                        "author_name": author.get("name"),
                        "verified": bool(author.get("verified")),
                        "lang": tweet.get("lang"),
                        "query": query,
                    },
                }
            )
        return items

    def fetch_user_recent_posts(self, username: str, max_results: int = 20) -> list[dict[str, Any]]:
        normalized = username.strip().lstrip("@")
        if not normalized or not self.enabled:
            return []
        query = f"from:{normalized} -is:retweet"
        return self.search_recent_posts(query=query, max_results=max_results)
