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
    event_zh: str
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
            content_excerpt = ""

        zh = "规则分类：命中 AI+区块链关键词，判定为潜在落地热点。" if decision.is_hotspot else "规则分类：未达到 AI+区块链落地热点阈值。"
        event_zh = self._heuristic_event_zh(
            title=raw_title,
            content_excerpt=content_excerpt,
            source_type=source_type,
        )
        insight_zh = self._heuristic_insight_zh(
            title=raw_title,
            content_excerpt=event_zh,
            source_type=source_type,
            engagement=engagement,
        )
        return SemanticClassification(
            is_ai_blockchain_adoption=decision.is_hotspot,
            category=decision.category,
            confidence=min(0.99, max(0.1, decision.score / 10)),
            summary_zh=zh,
            event_zh=event_zh,
            insight_zh=insight_zh,
        )

    def _heuristic_event_zh(
        self,
        *,
        title: str,
        content_excerpt: str,
        source_type: str,
    ) -> str:
        text = f"{title} {content_excerpt}".lower()
        if any(k in text for k in ("wrapped xrp", "xrp", "solana", "w xrp", "wxrp", "minted")):
            return "XRP 通过封装资产接入 Solana，核心是扩大在 DeFi 场景中的流动性与可组合性。"
        if any(k in text for k in ("investigation", "probe", "manipulation", "调查", "操纵")):
            return "该事件聚焦于交易操纵与合规调查，短期影响市场信任与流动性稳定。"
        if any(k in text for k in ("agent", "ai agents", "llm", "model", "inference")):
            return "消息显示 AI 代理在链上金融场景渗透加深，但在复杂策略执行上仍存在能力边界。"
        if any(k in text for k in ("release", "version", "bug fix", "maintenance", "security")):
            return "项目发布版本更新并修复关键问题，重点在提升节点稳定性、安全性与兼容性。"
        if any(k in text for k in ("exploit", "hack", "漏洞")):
            return "该消息属于安全事件更新，反映协议在攻击面治理与应急恢复上的现实压力。"
        if any(k in text for k in ("tvl", "volume", "users", "active")):
            return "该消息反映协议运营指标变化，关键在于热度是否转化为可持续链上行为。"
        if source_type in {"github_release", "github_trending"}:
            return "该更新主要是研发与工程进展信号，短期影响开发者生态与协议演进节奏。"
        if source_type in {"x", "x_kol", "x_kol_hot"}:
            return "该消息来自社交传播通道，需结合链上数据验证是否形成真实采用。"
        if source_type == "defillama":
            return "该消息反映协议运营指标变化，关键在于热度是否转化为可持续链上行为。"
        if source_type == "dune":
            return "该信号来自链上数据统计结果，重点是确认趋势是否具有连续性与可验证性。"
        if content_excerpt:
            return f"该消息核心信息：{content_excerpt}"
        return "该消息为生态动态更新，需结合后续链上数据与用户行为判断真实落地程度。"

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
            angles.append("落地判断：关注 2-4 周内新增地址留存、交易频次和复用率，确认是否从新闻热度转成持续使用。")
        if any(k in text for k in ("investigation", "probe", "lawsuit", "监管", "调查", "collapse")):
            angles.append("风险判断：合规与市场结构风险抬升，短期波动可能显著高于基本面改善速度。")
        if any(k in text for k in ("exploit", "hack", "漏洞", "security", "regression")):
            angles.append("安全判断：修复时长和补丁覆盖率将直接影响资金回流与开发者迁移意愿。")
        if any(k in text for k in ("wrapped", "bridge", "cross-chain", "跨链")):
            angles.append("结构判断：跨链带来流动性效率提升，但桥接依赖也会放大系统性风险传导。")
        if any(k in text for k in ("agent", "ai", "llm", "model", "inference")):
            angles.append("能力判断：AI 代理在规则化场景可替代人工，但复杂市场状态下仍依赖人机协同策略。")
        if any(k in text for k in ("tvl", "volume", "users", "active", "fees", "minted")):
            angles.append("验证路径：同步跟踪 TVL、活跃地址、协议费收入，判断叙事是否转化为可量化需求。")

        if source_type in {"github_release", "github_trending"}:
            angles.append("研发信号：继续跟踪贡献者增长、issue 关闭效率与版本发布节奏，判断工程化是否提速。")
        elif source_type in {"x", "x_kol"}:
            angles.append("传播信号：社交声量可能领先基本面，需防止“高热度低转化”。")
        elif source_type == "defillama":
            angles.append("指标解读：优先关注 TVL 与活跃用户的同向变化，避免仅由资金迁移造成的短期虚增。")
        elif source_type == "dune":
            angles.append("数据验证：建议持续观察 7-30 天窗口，确认该信号不是短周期统计噪声。")
        else:
            angles.append("执行建议：跟踪后续合作方、资金流向与用户行为，避免对单条新闻做趋势外推。")

        deduped: list[str] = []
        for angle in angles:
            if angle not in deduped:
                deduped.append(angle)
        selected = deduped[:3] if deduped else ["执行建议：优先观察链上真实数据，再决定是否提升监控权重。"]
        return "\n".join(selected)

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
            "is_ai_blockchain_adoption(bool), category(str), confidence(float 0-1), event_zh(str), insight_zh(str), summary_zh(str).\n"
            "Category examples: ai-blockchain-adoption, ai-token-hype, infra-update, ecosystem-news, generic-blockchain.\n"
            "event_zh should be Chinese interpretation of the core event in 1-2 sentences.\n"
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
            event_zh=str(parsed.get("event_zh") or "该消息为生态动态更新，需结合链上数据持续验证。"),
            insight_zh=str(parsed.get("insight_zh") or parsed.get("summary_zh") or "暂无中文观点"),
        )
