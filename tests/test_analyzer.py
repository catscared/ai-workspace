from hot_monitor.analyzer import evaluate_hotspot, relevance_score_for_target


def test_evaluate_hotspot_marks_ai_chain_content() -> None:
    decision = evaluate_hotspot(
        title="AI agent launch for DeFi",
        content="New onchain AI compute partnership with token incentives",
        source_type="news",
        engagement=0,
    )
    assert decision.is_hotspot
    assert decision.score >= 2.8
    assert decision.category == "ai-blockchain-adoption"


def test_relevance_score_for_target() -> None:
    score = relevance_score_for_target(
        text="Bittensor TAO announces AI compute subnet launch",
        keywords=["bittensor", "tao", "subnet"],
    )
    assert score == 1.0


def test_evaluate_hotspot_non_ai_content() -> None:
    decision = evaluate_hotspot(
        title="Random market summary",
        content="Traditional finance broad market moved today.",
        source_type="news",
        engagement=0,
    )
    assert decision.is_hotspot is False
