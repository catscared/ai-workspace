from __future__ import annotations

from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .config import Settings
from .service import HotMonitorService


def _parse_cron(cron_expr: str) -> CronTrigger:
    parts = [part.strip() for part in cron_expr.split(" ") if part.strip()]
    if len(parts) != 5:
        raise ValueError("COLLECTION_CRON must contain 5 fields: min hour day month dow")
    minute, hour, day, month, day_of_week = parts
    return CronTrigger(
        minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week
    )


def build_scheduler(service: HotMonitorService, settings: Settings) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    if settings.collection_interval_minutes > 0:
        scheduler.add_job(
            service.collect_and_analyze,
            IntervalTrigger(minutes=settings.collection_interval_minutes),
            id="collect-and-analyze",
            replace_existing=True,
        )
    else:
        scheduler.add_job(
            service.collect_and_analyze,
            _parse_cron(settings.collection_cron),
            id="collect-and-analyze",
            replace_existing=True,
        )
    return scheduler


def register_telegram_poll_job(
    scheduler: BackgroundScheduler,
    poller_callable: Callable[[], int],
    settings: Settings,
) -> None:
    scheduler.add_job(
        poller_callable,
        IntervalTrigger(seconds=max(5, settings.telegram_poll_interval_seconds)),
        id="telegram-command-poll",
        replace_existing=True,
    )
