from __future__ import annotations

from collections import defaultdict
from typing import Any

from .analyzer import relevance_score_for_target
from .config import Settings
from .database import Database
from .integrations.llm_classifier import LlmSemanticClassifier
from .integrations.telegram_bot import TelegramBotClient
from .sources.defillama import fetch_defillama_items
from .sources.dune import fetch_dune_items
from .sources.github_releases import fetch_github_release_items
from .sources.news_rss import fetch_news_items
from .sources.x_client import XClient


class HotMonitorService:
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.x_client = XClient(settings.x_bearer_token)
        self._event_keys_seen_in_run: set[tuple[int, int | None, int]] = set()
        self.telegram = TelegramBotClient(
            token=settings.telegram_bot_token,
            default_chat_id=settings.telegram_chat_id,
        )
        self.semantic_classifier = LlmSemanticClassifier(
            api_base_url=settings.llm_api_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
        self._last_telegram_digest = ""

    def _default_x_query(self) -> str:
        return (
            "(ai OR agent OR llm OR zkml OR depin OR compute) "
            "(blockchain OR web3 OR crypto OR token OR defi) lang:en -is:retweet"
        )

    def collect_and_analyze(self) -> dict[str, int]:
        inserted_raw_items = 0
        hotspots_detected = 0
        monitor_events_detected = 0
        self._event_keys_seen_in_run.clear()
        run_hotspots: list[dict[str, Any]] = []

        batch_items: list[dict[str, Any]] = []
        batch_items.extend(fetch_news_items(self.settings.news_rss_feeds))
        if self.settings.defillama_enabled:
            try:
                batch_items.extend(fetch_defillama_items())
            except Exception:
                pass
        try:
            batch_items.extend(
                fetch_dune_items(
                    api_key=self.settings.dune_api_key,
                    query_ids=self.settings.dune_query_ids,
                )
            )
        except Exception:
            pass
        try:
            batch_items.extend(
                fetch_github_release_items(
                    repos=self.settings.github_release_repos,
                    token=self.settings.github_token,
                )
            )
        except Exception:
            pass

        try:
            batch_items.extend(
                self.x_client.search_recent_posts(
                    query=self._default_x_query(),
                    max_results=self.settings.x_max_results,
                )
            )
        except Exception:
            # X API is optional for MVP; failures should not stop news collection.
            pass

        targets = self.db.list_watch_targets()
        kols = self.db.list_kol_accounts(min_followers=self.settings.kol_min_followers)
        target_to_kols = defaultdict(list)
        for link in self.db.list_target_kol_links():
            target_to_kols[link["target_id"]].append(link["kol_id"])
        kol_map = {k["id"]: k for k in kols}

        # Also fetch timelines from configured KOLs.
        for kol in kols:
            try:
                batch_items.extend(
                    self.x_client.fetch_user_recent_posts(
                        kol["handle"], max_results=self.settings.x_max_results
                    )
                )
            except Exception:
                continue

        for item in batch_items:
            raw_item_id, was_inserted = self.db.save_raw_item(**item)
            if was_inserted:
                inserted_raw_items += 1

            semantic = self.semantic_classifier.classify(
                title=item.get("title"),
                content=item.get("content"),
                source_type=item.get("source_type", "unknown"),
                engagement=item.get("engagement", 0),
            )
            if semantic.is_ai_blockchain_adoption:
                score = round(semantic.confidence * 10, 3)
                self.db.upsert_hotspot(
                    raw_item_id=raw_item_id,
                    score=score,
                    category=semantic.category,
                    summary=f"{semantic.summary_zh} | {semantic.summary_en}",
                    summary_zh=semantic.summary_zh,
                    summary_en=semantic.summary_en,
                    confidence=semantic.confidence,
                )
                run_hotspots.append(
                    {
                        "title": item.get("title") or (item.get("content") or "")[:80],
                        "url": item.get("url"),
                        "confidence": float(semantic.confidence),
                        "score": score,
                        "title_zh": semantic.title_zh,
                        "title_en": semantic.title_en,
                        "insight_zh": semantic.insight_zh,
                        "insight_en": semantic.insight_en,
                    }
                )
                hotspots_detected += 1

            text_for_matching = " ".join(
                part
                for part in [
                    item.get("title"),
                    item.get("content"),
                    item.get("author_handle"),
                ]
                if part
            )
            author_handle = (item.get("author_handle") or "").lower()
            author_followers = int(item.get("author_followers") or 0)

            for target in targets:
                score = relevance_score_for_target(text_for_matching, target["keywords"])
                if score < 0.35:
                    continue
                linked_kols = target_to_kols.get(target["id"], [])
                matched_kol_id: int | None = None
                for kol_id in linked_kols:
                    kol = kol_map.get(kol_id)
                    if not kol:
                        continue
                    if author_handle == kol["handle"].lower().lstrip("@"):
                        matched_kol_id = kol_id
                        break
                source_type = str(item.get("source_type") or "")
                if (
                    source_type == "x"
                    and matched_kol_id is None
                    and author_followers < self.settings.kol_min_followers
                ):
                    # For X content, require influencer threshold or explicit KOL mapping.
                    continue

                self.db.upsert_monitor_event(
                    target_id=target["id"],
                    kol_id=matched_kol_id,
                    raw_item_id=raw_item_id,
                    relevance_score=score,
                )
                event_key = (target["id"], matched_kol_id, raw_item_id)
                if event_key not in self._event_keys_seen_in_run:
                    self._event_keys_seen_in_run.add(event_key)
                    monitor_events_detected += 1

        result = {
            "inserted_raw_items": inserted_raw_items,
            "hotspots_detected": hotspots_detected,
            "monitor_events_detected": monitor_events_detected,
        }
        self._last_telegram_digest = self._build_hotspot_digest(hotspots=run_hotspots)
        if self.settings.telegram_notify_on_collect:
            self._notify_collect_result(self._last_telegram_digest)
        return result

    def get_last_telegram_digest(self) -> str:
        return self._last_telegram_digest

    def _build_hotspot_digest(self, *, hotspots: list[dict[str, Any]]) -> str:
        ranked = sorted(
            hotspots,
            key=lambda item: (float(item.get("confidence") or 0), float(item.get("score") or 0)),
            reverse=True,
        )[: max(1, self.settings.telegram_hotspot_push_limit)]

        lines = ["AI Hotspot Insights / AI热点深度观点"]
        if not ranked:
            lines.append("No hotspot detected / 本轮无热点")
            return "\n".join(lines)

        for idx, hotspot in enumerate(ranked, start=1):
            evidence_link = str(hotspot.get("url") or "").strip() or "N/A"
            title_zh = str(hotspot.get("title_zh") or hotspot.get("title") or "未命名热点")
            title_en = str(hotspot.get("title_en") or hotspot.get("title") or "Untitled hotspot")
            if len(evidence_link) > 400:
                evidence_link = evidence_link[:400].rstrip() + "..."
            lines.extend(
                [
                    "",
                    f"{idx}) 标题: {title_zh}",
                    f"   Title: {title_en}",
                    f"   AI观点(中文): {hotspot.get('insight_zh') or hotspot.get('summary_zh') or '暂无中文观点'}",
                    f"   AI Insight(EN): {hotspot.get('insight_en') or hotspot.get('summary_en') or 'No English insight'}",
                    f"   Link: {evidence_link}",
                ]
            )
        message = "\n".join(lines).strip()
        if len(message) > 3800:
            return message[:3790] + "\n..."
        return message

    def _notify_collect_result(self, message: str) -> None:
        try:
            self.telegram.send_message(message)
        except Exception:
            pass
