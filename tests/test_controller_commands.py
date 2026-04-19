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

    def get_last_digest_push_status(self) -> str:
        return "success"

    def get_last_digest_push_note(self) -> str:
        return ""


def test_collect_command_with_suffix_text() -> None:
    controller = TaskController(
        service=_ServiceStub(),
        scheduler=_SchedulerStub(),
        telegram=TelegramBotClient(token=""),
    )
    response = controller._handle_command("/collect 立即执行一次抓取")
    assert "Collected now." in response
    assert "raw_items=7" in response


def test_extract_command_handles_suffix_tokens() -> None:
    assert TaskController._extract_command("/collect now please") == "/collect"


def test_collect_completion_message_includes_push_status() -> None:
    class _ServiceWithPush(_ServiceStub):
        def get_last_digest_push_status(self) -> str:
            return "failed"

        def get_last_digest_push_note(self) -> str:
            return "telegram markdown parse error"

    controller = TaskController(
        service=_ServiceWithPush(),
        scheduler=_SchedulerStub(),
        telegram=TelegramBotClient(token=""),
    )
    resp = controller._handle_command("/collect")
    assert "digest_push=failed" in resp
    assert "telegram markdown parse error" in resp


def test_kol_whitelist_commands() -> None:
    class _ServiceWithWhitelist(_ServiceStub):
        def __init__(self) -> None:
            self.handles = [{"handle": "vitalikbuterin", "source": "telegram", "created_at": "now"}]

        def add_kol_whitelist_handle(self, handle: str):
            normalized = handle.strip().lstrip("@").lower()
            row = {"handle": normalized, "source": "telegram", "created_at": "now"}
            self.handles.append(row)
            return row

        def remove_kol_whitelist_handle(self, handle: str) -> bool:
            normalized = handle.strip().lstrip("@").lower()
            before = len(self.handles)
            self.handles = [r for r in self.handles if r["handle"] != normalized]
            return len(self.handles) < before

        def list_kol_whitelist_handles(self):
            return self.handles

    controller = TaskController(
        service=_ServiceWithWhitelist(),
        scheduler=_SchedulerStub(),
        telegram=TelegramBotClient(token=""),
    )
    assert "Usage: /kol_add" in controller._handle_command("/kol_add")
    assert "KOL whitelist added: @aeyakovenko" in controller._handle_command("/kol_add aeyakovenko")
    assert "KOL whitelist (" in controller._handle_command("/kol_list")
    assert "removed=True" in controller._handle_command("/kol_del aeyakovenko")
