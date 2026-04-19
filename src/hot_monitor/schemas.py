from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WatchTargetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    symbol: str | None = Field(default=None, max_length=20)
    keywords: list[str] = Field(default_factory=list, min_length=1)


class WatchTargetResponse(BaseModel):
    id: int
    name: str
    symbol: str | None
    keywords: list[str]
    created_at: datetime | str


class KolCreate(BaseModel):
    handle: str = Field(min_length=1, max_length=60)
    display_name: str | None = Field(default=None, max_length=120)
    followers: int = Field(ge=0)
    platform: str = Field(default="x", max_length=20)


class KolResponse(BaseModel):
    id: int
    handle: str
    display_name: str | None
    followers: int
    platform: str
    created_at: datetime | str


class BindKolRequest(BaseModel):
    kol_id: int


class CollectResult(BaseModel):
    inserted_raw_items: int
    hotspots_detected: int
    monitor_events_detected: int
