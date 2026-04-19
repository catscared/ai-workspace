from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from ..analyzer import evaluate_hotspot


@dataclass
class SemanticClassification:
    is_ai_blockchain_adoption: bool
    category: str
    confidence: float
    summary_zh: str
    summary_en: str


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
        zh = (
            "规则分类：命中 AI+区块链关键词，判定为潜在落地热点。"
            if decision.is_hotspot
            else "规则分类：未达到 AI+区块链落地热点阈值。"
        )
        en = (
            "Rule-based classification: matched AI + blockchain signals and marked as a potential adoption hotspot."
            if decision.is_hotspot
            else "Rule-based classification: does not meet the AI + blockchain adoption hotspot threshold."
        )
        return SemanticClassification(
            is_ai_blockchain_adoption=decision.is_hotspot,
            category=decision.category,
            confidence=min(0.99, max(0.1, decision.score / 10)),
            summary_zh=zh,
            summary_en=en,
        )

    def _classify_with_llm(
        self,
        *,
        title: str | None,
        content: str | None,
        source_type: str,
        engagement: int,
    ) -> SemanticClassification:
        prompt = (
            "You are a bilingual crypto intelligence classifier.\n"
            "Task: detect if content indicates real AI+blockchain application adoption/progress.\n"
            "Return strict JSON with keys: "
            "is_ai_blockchain_adoption(bool), category(str), confidence(float 0-1), summary_zh(str), summary_en(str).\n"
            "Category examples: ai-blockchain-adoption, ai-token-hype, infra-update, ecosystem-news, generic-blockchain.\n"
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
            summary_en=str(parsed.get("summary_en") or "No English summary"),
        )
