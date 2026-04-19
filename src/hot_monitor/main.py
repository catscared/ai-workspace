from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from .config import settings
from .controller import TaskController
from .database import Database
from .schemas import (
    BindKolRequest,
    CollectResult,
    KolWhitelistRequest,
    KolWhitelistResponse,
    KolCreate,
    KolResponse,
    TaskControlResponse,
    WatchTargetCreate,
    WatchTargetResponse,
)
from .scheduler import build_scheduler, register_telegram_poll_job
from .service import HotMonitorService


db = Database(settings.database_path)
service = HotMonitorService(db, settings)
scheduler = build_scheduler(service, settings)
controller = TaskController(service=service, scheduler=scheduler, telegram=service.telegram)
if service.telegram.enabled:
    register_telegram_poll_job(
        scheduler=scheduler,
        poller_callable=controller.poll_telegram_commands,
        settings=settings,
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/targets", response_model=WatchTargetResponse)
def create_target(payload: WatchTargetCreate) -> dict:
    if not payload.keywords:
        raise HTTPException(status_code=400, detail="At least one keyword is required")
    return db.create_watch_target(
        name=payload.name,
        symbol=payload.symbol,
        keywords=payload.keywords,
    )


@app.get("/targets", response_model=list[WatchTargetResponse])
def list_targets() -> list[dict]:
    return db.list_watch_targets()


@app.post("/kols", response_model=KolResponse)
def create_kol(payload: KolCreate) -> dict:
    if payload.followers < settings.kol_min_followers:
        raise HTTPException(
            status_code=400,
            detail=f"KOL followers must be >= {settings.kol_min_followers}",
        )
    return db.create_kol_account(
        handle=payload.handle,
        display_name=payload.display_name,
        followers=payload.followers,
        platform=payload.platform,
    )


@app.get("/kols", response_model=list[KolResponse])
def list_kols(
    min_followers: int = Query(
        default=settings.kol_min_followers, ge=0, description="Minimum followers filter"
    )
) -> list[dict]:
    return db.list_kol_accounts(min_followers=min_followers)


@app.post("/targets/{target_id}/kols")
def bind_kol(target_id: int, payload: BindKolRequest) -> dict[str, str]:
    try:
        db.get_watch_target(target_id)
        db.get_kol_account(payload.kol_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.map_target_kol(target_id=target_id, kol_id=payload.kol_id)
    return {"status": "linked"}


@app.get("/targets/{target_id}/kols", response_model=list[KolResponse])
def list_target_kols(target_id: int) -> list[dict]:
    try:
        db.get_watch_target(target_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return db.list_target_kols(target_id)


@app.post("/collect", response_model=CollectResult)
def collect_now() -> dict[str, int]:
    return service.collect_and_analyze()


@app.get("/kols/whitelist", response_model=list[KolWhitelistResponse])
def list_kol_whitelist() -> list[dict]:
    return service.list_kol_whitelist_handles()


@app.post("/kols/whitelist", response_model=KolWhitelistResponse)
def add_kol_whitelist(payload: KolWhitelistRequest) -> dict:
    try:
        return service.add_kol_whitelist_handle(payload.handle)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/kols/whitelist/{handle}")
def remove_kol_whitelist(handle: str) -> dict[str, bool]:
    removed = service.remove_kol_whitelist_handle(handle)
    return {"removed": removed}


@app.post("/tasks/stop", response_model=TaskControlResponse)
def stop_collect_task() -> dict[str, str | bool]:
    controller.pause_collection()
    state = controller.get_state()
    return {
        "status": "paused",
        "scheduler_running": state.scheduler_running,
        "collection_job_paused": state.collection_job_paused,
    }


@app.post("/tasks/start", response_model=TaskControlResponse)
def start_collect_task() -> dict[str, str | bool]:
    controller.resume_collection()
    state = controller.get_state()
    return {
        "status": "running",
        "scheduler_running": state.scheduler_running,
        "collection_job_paused": state.collection_job_paused,
    }


@app.get("/tasks/status", response_model=TaskControlResponse)
def task_status() -> dict[str, str | bool]:
    state = controller.get_state()
    return {
        "status": "paused" if state.collection_job_paused else "running",
        "scheduler_running": state.scheduler_running,
        "collection_job_paused": state.collection_job_paused,
    }


@app.get("/hotspots")
def list_hotspots(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    return db.list_hotspots(limit=limit)


@app.get("/monitor-events")
def list_monitor_events(
    limit: int = Query(default=100, ge=1, le=500),
    target_id: int | None = Query(default=None),
) -> list[dict]:
    return db.list_monitor_events(limit=limit, target_id=target_id)


@app.get("/telegram/last-digest")
def get_last_telegram_digest() -> dict[str, str]:
    return {"message": service.get_last_telegram_digest()}


@app.get("/config")
def get_runtime_config() -> dict[str, int | str | bool]:
    return {
        "collection_cron": settings.collection_cron,
        "collection_interval_minutes": settings.collection_interval_minutes,
        "kol_min_followers": settings.kol_min_followers,
        "x_max_results": settings.x_max_results,
        "telegram_enabled": service.telegram.enabled,
        "telegram_notify_on_collect": settings.telegram_notify_on_collect,
        "telegram_hotspot_push_limit": settings.telegram_hotspot_push_limit,
        "llm_enabled": service.semantic_classifier.enabled,
        "llm_model": settings.llm_model,
        "defillama_enabled": settings.defillama_enabled,
        "dune_query_ids": ",".join(settings.dune_query_ids),
        "github_release_repos": ",".join(settings.github_release_repos),
    }
