from __future__ import annotations

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
            paused = job.next_run_time is None
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
            response = self._handle_command(update.text)
            if response:
                try:
                    self.telegram.send_message(response, chat_id=update.chat_id)
                except Exception:
                    pass
            handled += 1
        return handled

    def _handle_command(self, text: str) -> str:
        cmd = text.strip().lower()
        if cmd in {"/task_stop", "/pause"}:
            self.pause_collection()
            return "Collection task paused."
        if cmd in {"/task_start", "/resume"}:
            self.resume_collection()
            return "Collection task resumed."
        if cmd == "/collect":
            result = self.service.collect_and_analyze()
            return (
                "Collected now.\n"
                f"raw_items={result['inserted_raw_items']}, "
                f"hotspots={result['hotspots_detected']}, "
                f"monitor_events={result['monitor_events_detected']}"
            )
        if cmd in {"/status", "/task_status"}:
            state = self.get_state()
            return (
                f"scheduler_running={state.scheduler_running}, "
                f"collection_job_paused={state.collection_job_paused}"
            )
        return "Unsupported command. Use /collect /task_start /task_stop /status"
