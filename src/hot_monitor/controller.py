from __future__ import annotations

import secrets
from dataclasses import dataclass

from apscheduler.schedulers.background import BackgroundScheduler

from .integrations.telegram_bot import TelegramBotClient
from .service import HotMonitorService


@dataclass
class TaskState:
    scheduler_running: bool
    collection_job_paused: bool


class TaskController:
    def __init__(
        self,
        *,
        service: HotMonitorService,
        scheduler: BackgroundScheduler,
        telegram: TelegramBotClient,
    ) -> None:
        self.service = service
        self.scheduler = scheduler
        self.telegram = telegram
        self._telegram_offset: int | None = None

    def pause_collection(self) -> None:
        job = self.scheduler.get_job("collect-and-analyze")
        if job is not None:
            self.scheduler.pause_job("collect-and-analyze")

    def resume_collection(self) -> None:
        job = self.scheduler.get_job("collect-and-analyze")
        if job is not None:
            self.scheduler.resume_job("collect-and-analyze")

    def get_state(self) -> TaskState:
        job = self.scheduler.get_job("collect-and-analyze")
        paused = False
        if job is None:
            paused = True
        else:
            # APScheduler may return pending Job objects before scheduler starts,
            # where next_run_time is not initialized yet.
            next_run_time = getattr(job, "next_run_time", None)
            paused = next_run_time is None
        return TaskState(
            scheduler_running=self.scheduler.running,
            collection_job_paused=paused,
        )

    def poll_telegram_commands(self) -> int:
        if not self.telegram.enabled:
            return 0
        updates = self.telegram.get_updates(
            offset=self._telegram_offset,
            timeout=10,
        )
        handled = 0
        for update in updates:
            self._telegram_offset = update.update_id + 1
            cmd = self._extract_command(update.text)
            receipt_id = self._build_receipt_id()
            if cmd == "/collect":
                start_message = f"[{receipt_id}] 任务已启动：正在执行抓取与分析..."
                try:
                    self.telegram.send_message(start_message, chat_id=update.chat_id)
                except Exception:
                    pass
            try:
                response = self._handle_command(update.text)
            except Exception as exc:
                response = f"[{receipt_id}] 任务执行失败：{exc}"
            if cmd == "/collect" and response:
                push_status = self.service.get_last_digest_push_status()
                push_note = self.service.get_last_digest_push_note()
                push_msg = (
                    "热点消息推送成功。"
                    if push_status == "success"
                    else f"热点消息推送失败：{push_note or 'unknown error'}"
                )
                response = (
                    f"[{receipt_id}] 任务完成：\n"
                    f"{response}\n\n"
                    f"[{receipt_id}] {push_msg}"
                )
            if response:
                try:
                    self.telegram.send_message(response, chat_id=update.chat_id)
                except Exception:
                    pass
            handled += 1
        return handled

    def _handle_command(self, text: str) -> str:
        cmd = self._extract_command(text)
        args = self._extract_args(text)
        if cmd in {"/task_stop", "/pause"}:
            self.pause_collection()
            return "Collection task paused."
        if cmd in {"/task_start", "/resume"}:
            self.resume_collection()
            return "Collection task resumed."
        if cmd == "/collect":
            result = self.service.collect_and_analyze()
            push_status_fn = getattr(self.service, "get_last_digest_push_status", None)
            push_note_fn = getattr(self.service, "get_last_digest_push_note", None)
            push_status = push_status_fn() if callable(push_status_fn) else "unknown"
            push_note = push_note_fn() if callable(push_note_fn) else ""
            return (
                "Collected now.\n"
                f"raw_items={result['inserted_raw_items']}, "
                f"hotspots={result['hotspots_detected']}, "
                f"monitor_events={result['monitor_events_detected']}, "
                f"digest_push={push_status}"
                + (f" ({push_note})" if push_note else "")
            )
        if cmd == "/kol_add":
            if not args:
                return "Usage: /kol_add <x_handle>"
            added = self.service.add_kol_whitelist_handle(args)
            return f"KOL whitelist added: @{added['handle']}"
        if cmd == "/kol_del":
            if not args:
                return "Usage: /kol_del <x_handle>"
            removed = self.service.remove_kol_whitelist_handle(args)
            return f"KOL whitelist removed={removed}: @{args.strip().lstrip('@').lower()}"
        if cmd == "/kol_list":
            rows = self.service.list_kol_whitelist_handles()
            if not rows:
                return "KOL whitelist is empty."
            handles = ", ".join(f"@{row['handle']}" for row in rows[:40])
            return f"KOL whitelist ({len(rows)}): {handles}"
        if cmd in {"/status", "/task_status"}:
            state = self.get_state()
            return (
                f"scheduler_running={state.scheduler_running}, "
                f"collection_job_paused={state.collection_job_paused}"
            )
        return "Unsupported command. Use /collect /task_start /task_stop /status /kol_add /kol_del /kol_list"

    @staticmethod
    def _extract_command(text: str) -> str:
        stripped = text.strip().lower()
        if not stripped:
            return ""
        return stripped.split()[0]

    @staticmethod
    def _extract_args(text: str) -> str:
        stripped = text.strip()
        if not stripped:
            return ""
        parts = stripped.split(maxsplit=1)
        if len(parts) < 2:
            return ""
        return parts[1].strip()

    @staticmethod
    def _build_receipt_id() -> str:
        return secrets.token_hex(4).upper()
