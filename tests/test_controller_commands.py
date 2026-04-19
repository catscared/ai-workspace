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
        return {"inserted_raw_items": 7, "hotspots_detected": 3, "monitor_events_detected": 2}


def test_collect_command_with_suffix_text() -> None:
    controller = TaskController(
        service=_ServiceStub(),
        scheduler=_SchedulerStub(),
        telegram=TelegramBotClient(token=""),
    )
    response = controller._handle_command("/collect 立即执行一次抓取")
    assert "Collected now." in response
    assert "raw_items=7" in response
