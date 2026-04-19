from __future__ import annotations

from typing import Any

import httpx


def fetch_github_release_items(
    repos: tuple[str, ...], token: str = "", max_releases_per_repo: int = 5
) -> list[dict[str, Any]]:
    normalized_repos = [repo.strip() for repo in repos if repo.strip()]
    if not normalized_repos:
        return []

    headers = {"Accept": "application/vnd.github+json"}
    if token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"

    items: list[dict[str, Any]] = []
    with httpx.Client(timeout=20.0, headers=headers) as client:
        for repo in normalized_repos:
            response = client.get(f"https://api.github.com/repos/{repo}/releases")
            response.raise_for_status()
            releases = response.json()
            for release in releases[:max_releases_per_repo]:
                release_id = release.get("id")
                if release_id is None:
                    continue
                body = str(release.get("body") or "")
                items.append(
                    {
                        "source_type": "github_release",
                        "external_id": f"github_release:{repo}:{release_id}",
                        "title": f"{repo} release: {release.get('tag_name') or release.get('name')}",
                        "content": body[:3000],
                        "author_handle": str((release.get("author") or {}).get("login") or "github"),
                        "author_followers": None,
                        "url": release.get("html_url"),
                        "published_at": release.get("published_at"),
                        "engagement": int((release.get("reactions") or {}).get("total_count") or 0),
                        "metadata": {
                            "repo": repo,
                            "tag_name": release.get("tag_name"),
                            "draft": bool(release.get("draft")),
                            "prerelease": bool(release.get("prerelease")),
                        },
                    }
                )
    return items
