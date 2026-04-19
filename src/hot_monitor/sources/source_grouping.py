from __future__ import annotations

from typing import Any


def resolve_channel(item: dict[str, Any]) -> str:
    metadata = item.get("metadata") or {}
    channel = str(metadata.get("channel") or "").strip().lower()
    if channel:
        return channel

    source_type = str(item.get("source_type") or "").strip().lower()
    if source_type in {"news", "chain_news"}:
        return source_type
    if source_type in {"x", "x_kol"}:
        return "x_kol" if metadata.get("kol_handle") else "x"
    if source_type in {"github_release", "github_trending", "dune", "defillama"}:
        return source_type
    return "other"


def channel_title(channel: str) -> str:
    mapping = {
        "news": "权威区块链媒体",
        "chain_news": "主流大链新闻(BTC/ETH/SOL)",
        "x": "X 热门话题",
        "x_kol": "X 大V/KOL 动态",
        "github_trending": "GitHub 热门飙升项目",
        "github_release": "GitHub 项目版本发布",
        "dune": "Dune 链上数据信号",
        "defillama": "DefiLlama 协议信号",
        "other": "其他来源",
    }
    return mapping.get(channel, channel)
