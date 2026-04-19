from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass

import httpx

from ..analyzer import evaluate_hotspot


@dataclass
class SemanticClassification:
    is_ai_blockchain_adoption: bool
    category: str
    confidence: float
    summary_zh: str
    insight_zh: str


class LlmSemanticClassifier:
    def __init__(
        self,
        *,
        api_base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.model = model
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def classify(
        self,
        *,
        title: str | None,
        content: str | None,
        source_type: str,
        engagement: int,
    ) -> SemanticClassification:
        if not self.enabled:
            return self._fallback(title=title, content=content, source_type=source_type, engagement=engagement)
        try:
            return self._classify_with_llm(
                title=title,
                content=content,
                source_type=source_type,
                engagement=engagement,
            )
        except Exception:
            return self._fallback(title=title, content=content, source_type=source_type, engagement=engagement)

    def _fallback(
        self,
        *,
        title: str | None,
        content: str | None,
        source_type: str,
        engagement: int,
    ) -> SemanticClassification:
        decision = evaluate_hotspot(
            title=title,
            content=content,
            source_type=source_type,
            engagement=engagement,
        )
        raw_title = self._clean_text(title) or "热点信号"
        cleaned_content = self._clean_text(content)
        content_excerpt = cleaned_content[:220].rstrip() + "..." if len(cleaned_content) > 220 else cleaned_content
        if not content_excerpt:
            content_excerpt = "No detailed content was available."

        zh = "规则分类：命中 AI+区块链关键词，判定为潜在落地热点。" if decision.is_hotspot else "规则分类：未达到 AI+区块链落地热点阈值。"
        insight_zh = self._heuristic_insight_zh(
            title=raw_title,
            content_excerpt=content_excerpt,
            source_type=source_type,
            engagement=engagement,
        )
        return SemanticClassification(
            is_ai_blockchain_adoption=decision.is_hotspot,
            category=decision.category,
            confidence=min(0.99, max(0.1, decision.score / 10)),
            summary_zh=zh,
            insight_zh=insight_zh,
        )

    def _heuristic_insight_zh(
        self,
        *,
        title: str,
        content_excerpt: str,
        source_type: str,
        engagement: int,
    ) -> str:
        text = f"{title} {content_excerpt}".lower()
        angles: list[str] = []
        if any(k in text for k in ("launch", "mainnet", "上线", "发布", "mint", "minted")):
            angles.append("该事件更像是产品化落地阶段信号，关键在于后续 2-4 周是否出现真实留存和链上复用。")
        if any(k in text for k in ("investigation", "probe", "lawsuit", "监管", "调查", "collapse")):
            angles.append("当前叙事存在合规与市场结构风险，短期价格波动可能高于基本面改善速度。")
        if any(k in text for k in ("exploit", "hack", "漏洞", "security", "regression")):
            angles.append("基础设施安全性是 AI+链上应用的硬门槛，若修复周期过长会直接压制开发者与资金迁移意愿。")
        if any(k in text for k in ("wrapped", "bridge", "cross-chain", "跨链")):
            angles.append("跨链可组合性提升了流动性效率，但也会放大桥接依赖与系统性风险传导。")
        if any(k in text for k in ("agent", "ai", "llm", "model", "inference")):
            angles.append("AI 要素已进入链上业务闭环，下一阶段应重点验证成本结构是否能支持可持续推理与结算。")
        if any(k in text for k in ("tvl", "volume", "users", "active", "fees", "minted")):
            angles.append("建议同步观察 TVL、活跃地址、协议费收入三项指标，判断叙事是否转化为可量化需求。")

        if source_type in {"github_release", "github_trending"}:
            angles.append("从研发视角看，应继续跟踪贡献者增长、issue 关闭效率与版本发布节奏，确认是否进入工程化加速期。")
        elif source_type in {"x", "x_kol"}:
            angles.append("该信号在社交媒体传播效率较高，需防止“高热度低转化”，应配合链上数据验证真实采用。")
        else:
            angles.append("建议重点跟踪后续合作方、资金流向和用户行为数据，避免仅凭单条新闻做趋势外推。")

        selected = angles[:3]
        return f"事件要点：{content_excerpt} AI深度观点：{' '.join(selected)}"

    @staticmethod
    def _clean_text(value: str | None) -> str:
        raw = (value or "").strip()
        if not raw:
            return ""
        normalized = html.unescape(raw)
        normalized = re.sub(r"<[^>]+>", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _classify_with_llm(
        self,
        *,
        title: str | None,
        content: str | None,
        source_type: str,
        engagement: int,
    ) -> SemanticClassification:
        prompt = (
            "You are a crypto intelligence classifier.\n"
            "Task: detect if content indicates real AI+blockchain application adoption/progress.\n"
            "Return strict JSON with keys: "
            "is_ai_blockchain_adoption(bool), category(str), confidence(float 0-1), insight_zh(str), summary_zh(str).\n"
            "Category examples: ai-blockchain-adoption, ai-token-hype, infra-update, ecosystem-news, generic-blockchain.\n"
            "insight_zh should be a deeper Chinese AI-oriented viewpoint summary (3-5 sentences), "
            "focusing on adoption feasibility, infra impact, token/value-capture implications, execution risk, and next watch points.\n"
            f"source_type={source_type}; engagement={engagement}\n"
            f"title={title or ''}\n"
            f"content={content or ''}\n"
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Output JSON only, no markdown."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.api_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        content_text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "{}")
        )
        parsed = json.loads(content_text)
        return SemanticClassification(
            is_ai_blockchain_adoption=bool(parsed.get("is_ai_blockchain_adoption", False)),
            category=str(parsed.get("category") or "generic-blockchain"),
            confidence=float(parsed.get("confidence") or 0.5),
            summary_zh=str(parsed.get("summary_zh") or "暂无中文摘要"),
            insight_zh=str(parsed.get("insight_zh") or parsed.get("summary_zh") or "暂无中文观点"),
        )
