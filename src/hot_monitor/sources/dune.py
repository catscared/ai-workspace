from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx


def fetch_dune_items(api_key: str, query_ids: tuple[str, ...], max_rows: int = 10) -> list[dict[str, Any]]:
    key = api_key.strip()
    if not key or not query_ids:
        return []

    items: list[dict[str, Any]] = []
    headers = {"X-Dune-API-Key": key}
    with httpx.Client(timeout=20.0) as client:
        for query_id in query_ids:
            query_id = query_id.strip()
            if not query_id:
                continue
            response = client.get(
                f"https://api.dune.com/api/v1/query/{query_id}/results",
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
            rows = (payload.get("result") or {}).get("rows") or []
            execution = payload.get("execution_ended_at") or datetime.now(timezone.utc).isoformat()
            for idx, row in enumerate(rows[:max_rows]):
                row_text = ", ".join(f"{k}={v}" for k, v in row.items())
                external_id = f"dune:{query_id}:{idx}"
                items.append(
                    {
                        "source_type": "dune",
                        "external_id": external_id,
                        "title": f"Dune query {query_id} signal",
                        "content": row_text[:2000],
                        "author_handle": "dune",
                        "author_followers": None,
                        "url": f"https://dune.com/queries/{query_id}",
                        "published_at": str(execution),
                        "engagement": 0,
                        "metadata": {
                            "query_id": query_id,
                            "row_index": idx,
                        },
                    }
                )
    return items
