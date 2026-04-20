from hot_monitor.sources.source_grouping import channel_title, resolve_channel


def test_resolve_channel_prefers_metadata_channel() -> None:
    item = {"source_type": "news", "metadata": {"channel": "chain_news"}}
    assert resolve_channel(item) == "chain_news"


def test_resolve_channel_falls_back_to_source_type() -> None:
    assert resolve_channel({"source_type": "github_trending", "metadata": {}}) == "github_trending"
    assert resolve_channel({"source_type": "x", "metadata": {"kol_handle": "vitalik"}}) == "x_kol"


def test_channel_title_mapping() -> None:
    assert channel_title("x_kol") == "X 大V/KOL 动态"
    assert channel_title("x_kol_hot") == "X 大V/KOL 热门帖子"
