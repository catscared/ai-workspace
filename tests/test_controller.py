from __future__ import annotations

from hot_monitor.controller import TaskController
from hot_monitor.integrations.telegram_bot import TelegramBotClient


class _Job:
    def __init__(self, next_run_time: object) -> None:
        self.next_run_time = next_run_time


class _SchedulerStub:
    def __init__(self) -> None:
        self.running = True
        self.paused = False

    def get_job(self, _: str):
        if self.paused:
            return _Job(next_run_time=None)
        return _Job(next_run_time=object())

    def pause_job(self, _: str) -> None:
        self.paused = True

    def resume_job(self, _: str) -> None:
        self.paused = False


class _ServiceStub:
    def collect_and_analyze(self) -> dict[str, int]:
        return {"inserted_raw_items": 1, "hotspots_detected": 2, "monitor_events_detected": 3}


def test_task_controller_pause_resume() -> None:
    scheduler = _SchedulerStub()
    controller = TaskController(
        service=_ServiceStub(),
        scheduler=scheduler,
        telegram=TelegramBotClient(token=""),
    )
    controller.pause_collection()
    assert controller.get_state().collection_job_paused is True
    controller.resume_collection()
    assert controller.get_state().collection_job_paused is False
