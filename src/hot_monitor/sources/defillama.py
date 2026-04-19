from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx


def fetch_defillama_items(max_items: int = 20) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    url = "https://api.llama.fi/protocols"
    with httpx.Client(timeout=20.0) as client:
        response = client.get(url)
        response.raise_for_status()
        payload = response.json()
    now = datetime.now(timezone.utc).isoformat()
    for protocol in payload[:max_items]:
        name = str(protocol.get("name") or "").strip()
        if not name:
            continue
        symbol = str(protocol.get("symbol") or "").strip()
        tvl = protocol.get("tvl")
        category = str(protocol.get("category") or "unknown")
        chain = str(protocol.get("chain") or "multi-chain")
        change_1d = protocol.get("change_1d")
        content = (
            f"DefiLlama protocol snapshot: name={name}, symbol={symbol}, "
            f"category={category}, chain={chain}, tvl={tvl}, change_1d={change_1d}"
        )
        slug = str(protocol.get("slug") or "").strip()
        if slug:
            protocol_url = f"https://defillama.com/protocol/{slug}"
        else:
            protocol_url = "https://defillama.com/protocols"
        items.append(
            {
                "source_type": "defillama",
                "external_id": f"defillama:{name}",
                "title": f"DefiLlama update: {name}",
                "content": content,
                "author_handle": "defillama",
                "author_followers": None,
                "url": protocol_url,
                "published_at": now,
                "engagement": int(abs(float(change_1d or 0))),
                "metadata": {
                    "symbol": symbol,
                    "category": category,
                    "chain": chain,
                    "tvl": tvl,
                    "change_1d": change_1d,
                },
            }
        )
    return items
