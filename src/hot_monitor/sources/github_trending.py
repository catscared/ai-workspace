from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx


def fetch_github_trending_items(
    *,
    query: str,
    token: str = "",
    max_results: int = 15,
    min_stars: int = 150,
) -> list[dict[str, Any]]:
    normalized_query = query.strip()
    if not normalized_query:
        return []

    headers = {"Accept": "application/vnd.github+json"}
    if token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"

    params = {
        "q": f"{normalized_query} stars:>={max(0, min_stars)}",
        "sort": "updated",
        "order": "desc",
        "per_page": max(1, min(max_results, 50)),
    }
    with httpx.Client(timeout=20.0, headers=headers) as client:
        response = client.get("https://api.github.com/search/repositories", params=params)
        response.raise_for_status()
        payload = response.json()

    items: list[dict[str, Any]] = []
    for repo in payload.get("items", []):
        repo_id = repo.get("id")
        full_name = str(repo.get("full_name") or "").strip()
        if not repo_id or not full_name:
            continue
        stars = int(repo.get("stargazers_count") or 0)
        forks = int(repo.get("forks_count") or 0)
        language = str(repo.get("language") or "")
        description = str(repo.get("description") or "")
        content = (
            f"GitHub 热门仓库: {full_name}; stars={stars}; forks={forks}; "
            f"language={language}; description={description}"
        )
        items.append(
            {
                "source_type": "github_trending",
                "external_id": f"github_trending:{repo_id}",
                "title": f"GitHub 热门项目: {full_name}",
                "content": content,
                "author_handle": str((repo.get("owner") or {}).get("login") or "github"),
                "author_followers": None,
                "url": repo.get("html_url"),
                "published_at": repo.get("updated_at") or datetime.now(timezone.utc).isoformat(),
                "engagement": stars + forks,
                "metadata": {
                    "repo": full_name,
                    "stars": stars,
                    "forks": forks,
                    "language": language,
                    "channel": "github_trending",
                },
            }
        )
    return items
