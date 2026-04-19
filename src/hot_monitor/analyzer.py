from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


AI_BLOCKCHAIN_KEYWORDS = (
    "ai",
    "agent",
    "llm",
    "model",
    "inference",
    "depin",
    "compute",
    "gpu",
    "zkml",
    "data availability",
    "rollup",
    "web3 ai",
    "blockchain ai",
    "onchain ai",
    "token",
    "defi",
    "dao",
    "launch",
    "integration",
    "partnership",
    "mainnet",
)


@dataclass
class HotspotDecision:
    is_hotspot: bool
    score: float
    category: str
    summary: str


def _normalize_text(*parts: str | None) -> str:
    return " ".join(part.strip() for part in parts if part).lower()


def evaluate_hotspot(
    *,
    title: str | None,
    content: str | None,
    source_type: str,
    engagement: int = 0,
) -> HotspotDecision:
    text = _normalize_text(title, content)
    if not text:
        return HotspotDecision(False, 0.0, "unknown", "No analyzable content")

    keyword_hits = [kw for kw in AI_BLOCKCHAIN_KEYWORDS if kw in text]
    keyword_score = len(keyword_hits) * 1.4

    engagement_score = 0.0
    if source_type == "x":
        engagement_score = min(6.0, engagement / 8000.0)
    elif source_type == "news":
        engagement_score = 1.0

    score = round(keyword_score + engagement_score, 3)
    category = "ai-blockchain-adoption" if keyword_hits else "generic-blockchain"
    summary = (
        f"Matched {len(keyword_hits)} AI/blockchain keyword(s): "
        + ", ".join(keyword_hits[:8])
        if keyword_hits
        else "No AI/blockchain keywords matched."
    )
    is_hotspot = score >= 2.8 and bool(keyword_hits)
    return HotspotDecision(is_hotspot, score, category, summary)


def relevance_score_for_target(text: str, keywords: Iterable[str]) -> float:
    lowered_text = text.lower()
    normalized = [kw.lower().strip() for kw in keywords if kw.strip()]
    if not normalized:
        return 0.0
    hits = sum(1 for kw in normalized if kw in lowered_text)
    return round(hits / len(normalized), 3)
