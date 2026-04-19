from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._ensure_parent_dir()
        self._init_schema()

    def _ensure_parent_dir(self) -> None:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        self._ensure_parent_dir()
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        if not self._schema_exists(conn):
            self._apply_schema(conn)
        return conn

    def _init_schema(self) -> None:
        with self._get_conn() as conn:
            self._apply_schema(conn)

    def _apply_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
                CREATE TABLE IF NOT EXISTS watch_targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    symbol TEXT,
                    keywords TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS kol_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    handle TEXT NOT NULL UNIQUE,
                    display_name TEXT,
                    followers INTEGER NOT NULL,
                    platform TEXT NOT NULL DEFAULT 'x',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS target_kol_map (
                    target_id INTEGER NOT NULL,
                    kol_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (target_id, kol_id),
                    FOREIGN KEY(target_id) REFERENCES watch_targets(id) ON DELETE CASCADE,
                    FOREIGN KEY(kol_id) REFERENCES kol_accounts(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS x_kol_whitelist (
                    handle TEXT PRIMARY KEY,
                    source TEXT NOT NULL DEFAULT 'manual',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS raw_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    author_handle TEXT,
                    author_followers INTEGER,
                    title TEXT,
                    content TEXT,
                    url TEXT,
                    published_at TEXT,
                    engagement INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    ingested_at TEXT NOT NULL,
                    UNIQUE(source_type, external_id)
                );

                CREATE TABLE IF NOT EXISTS hotspots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_item_id INTEGER NOT NULL,
                    score REAL NOT NULL,
                    category TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    summary_zh TEXT NOT NULL DEFAULT '',
                    summary_en TEXT NOT NULL DEFAULT '',
                    confidence REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    UNIQUE(raw_item_id),
                    FOREIGN KEY(raw_item_id) REFERENCES raw_items(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS monitor_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_id INTEGER NOT NULL,
                    kol_id INTEGER,
                    raw_item_id INTEGER NOT NULL,
                    relevance_score REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(target_id, kol_id, raw_item_id),
                    FOREIGN KEY(target_id) REFERENCES watch_targets(id) ON DELETE CASCADE,
                    FOREIGN KEY(kol_id) REFERENCES kol_accounts(id) ON DELETE CASCADE,
                    FOREIGN KEY(raw_item_id) REFERENCES raw_items(id) ON DELETE CASCADE
                );
            """
        )
        self._ensure_hotspot_columns(conn)

    @staticmethod
    def _schema_exists(conn: sqlite3.Connection) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'watch_targets'"
        ).fetchone()
        return row is not None

    @staticmethod
    def _ensure_hotspot_columns(conn: sqlite3.Connection) -> None:
        existing_cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(hotspots)").fetchall()
        }
        if "summary_zh" not in existing_cols:
            conn.execute("ALTER TABLE hotspots ADD COLUMN summary_zh TEXT NOT NULL DEFAULT ''")
        if "summary_en" not in existing_cols:
            conn.execute("ALTER TABLE hotspots ADD COLUMN summary_en TEXT NOT NULL DEFAULT ''")
        if "confidence" not in existing_cols:
            conn.execute("ALTER TABLE hotspots ADD COLUMN confidence REAL NOT NULL DEFAULT 0")

    def create_watch_target(self, name: str, symbol: str | None, keywords: list[str]) -> dict[str, Any]:
        with self._get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO watch_targets (name, symbol, keywords, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (name, symbol, json.dumps(keywords, ensure_ascii=True), _utc_now()),
            )
            target_id = cur.lastrowid
        return self.get_watch_target(target_id)

    def list_watch_targets(self) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, name, symbol, keywords, created_at FROM watch_targets ORDER BY id DESC"
            ).fetchall()
        return [self._decode_target_row(row) for row in rows]

    def get_watch_target(self, target_id: int) -> dict[str, Any]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT id, name, symbol, keywords, created_at FROM watch_targets WHERE id = ?",
                (target_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"Watch target {target_id} not found")
        return self._decode_target_row(row)

    @staticmethod
    def _decode_target_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "symbol": row["symbol"],
            "keywords": json.loads(row["keywords"] or "[]"),
            "created_at": row["created_at"],
        }

    def create_kol_account(
        self, handle: str, display_name: str | None, followers: int, platform: str = "x"
    ) -> dict[str, Any]:
        with self._get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO kol_accounts (handle, display_name, followers, platform, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(handle) DO UPDATE SET
                    display_name = excluded.display_name,
                    followers = excluded.followers,
                    platform = excluded.platform
                """,
                (handle, display_name, followers, platform, _utc_now()),
            )
            kol_id = cur.lastrowid
            if not kol_id:
                existing = conn.execute(
                    "SELECT id FROM kol_accounts WHERE handle = ?", (handle,)
                ).fetchone()
                if existing is None:
                    raise ValueError("Unable to create KOL account")
                kol_id = existing["id"]
        return self.get_kol_account(kol_id)

    def get_kol_account(self, kol_id: int) -> dict[str, Any]:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT id, handle, display_name, followers, platform, created_at
                FROM kol_accounts
                WHERE id = ?
                """,
                (kol_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"KOL account {kol_id} not found")
        return dict(row)

    def list_kol_accounts(self, min_followers: int = 0) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, handle, display_name, followers, platform, created_at
                FROM kol_accounts
                WHERE followers >= ?
                ORDER BY followers DESC, id DESC
                """,
                (min_followers,),
            ).fetchall()
        return [dict(row) for row in rows]

    def map_target_kol(self, target_id: int, kol_id: int) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO target_kol_map (target_id, kol_id, created_at)
                VALUES (?, ?, ?)
                """,
                (target_id, kol_id, _utc_now()),
            )

    def list_target_kol_links(self) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT target_id, kol_id, created_at
                FROM target_kol_map
                ORDER BY target_id, kol_id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def list_target_kols(self, target_id: int) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT k.id, k.handle, k.display_name, k.followers, k.platform, k.created_at
                FROM kol_accounts k
                INNER JOIN target_kol_map m ON m.kol_id = k.id
                WHERE m.target_id = ?
                ORDER BY k.followers DESC
                """,
                (target_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_x_kol_whitelist_handle(self, handle: str, source: str = "manual") -> dict[str, Any]:
        normalized = handle.strip().lstrip("@").lower()
        if not normalized:
            raise ValueError("KOL handle is required")
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO x_kol_whitelist (handle, source, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(handle) DO UPDATE SET source = excluded.source
                """,
                (normalized, source, _utc_now()),
            )
            row = conn.execute(
                "SELECT handle, source, created_at FROM x_kol_whitelist WHERE handle = ?",
                (normalized,),
            ).fetchone()
        if row is None:
            raise ValueError("Unable to persist KOL whitelist handle")
        return dict(row)

    def remove_x_kol_whitelist_handle(self, handle: str) -> bool:
        normalized = handle.strip().lstrip("@").lower()
        if not normalized:
            return False
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM x_kol_whitelist WHERE handle = ?", (normalized,))
        return cur.rowcount > 0

    def list_x_kol_whitelist_handles(self) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT handle, source, created_at
                FROM x_kol_whitelist
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def save_raw_item(
        self,
        *,
        source_type: str,
        external_id: str,
        title: str | None,
        content: str | None,
        author_handle: str | None,
        author_followers: int | None,
        url: str | None,
        published_at: str | None,
        engagement: int,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[int, bool]:
        metadata_json = json.dumps(metadata or {}, ensure_ascii=True)
        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM raw_items WHERE source_type = ? AND external_id = ?",
                (source_type, external_id),
            ).fetchone()
            was_inserted = existing is None
            conn.execute(
                """
                INSERT INTO raw_items (
                    source_type, external_id, author_handle, author_followers, title,
                    content, url, published_at, engagement, metadata_json, ingested_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_type, external_id) DO UPDATE SET
                    author_handle = excluded.author_handle,
                    author_followers = excluded.author_followers,
                    title = excluded.title,
                    content = excluded.content,
                    url = excluded.url,
                    published_at = excluded.published_at,
                    engagement = excluded.engagement,
                    metadata_json = excluded.metadata_json
                """,
                (
                    source_type,
                    external_id,
                    author_handle,
                    author_followers,
                    title,
                    content,
                    url,
                    published_at,
                    engagement,
                    metadata_json,
                    _utc_now(),
                ),
            )
            row = conn.execute(
                "SELECT id FROM raw_items WHERE source_type = ? AND external_id = ?",
                (source_type, external_id),
            ).fetchone()
        if row is None:
            raise ValueError("Unable to persist raw item")
        return int(row["id"]), bool(was_inserted)

    def upsert_hotspot(
        self,
        raw_item_id: int,
        score: float,
        category: str,
        summary: str,
        summary_zh: str = "",
        summary_en: str = "",
        confidence: float = 0.0,
    ) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO hotspots (
                    raw_item_id, score, category, summary, summary_zh, summary_en, confidence, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(raw_item_id) DO UPDATE SET
                    score = excluded.score,
                    category = excluded.category,
                    summary = excluded.summary,
                    summary_zh = excluded.summary_zh,
                    summary_en = excluded.summary_en,
                    confidence = excluded.confidence,
                    created_at = excluded.created_at
                """,
                (raw_item_id, score, category, summary, summary_zh, summary_en, confidence, _utc_now()),
            )

    def upsert_monitor_event(
        self, target_id: int, kol_id: int | None, raw_item_id: int, relevance_score: float
    ) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO monitor_events (
                    target_id, kol_id, raw_item_id, relevance_score, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(target_id, kol_id, raw_item_id) DO UPDATE SET
                    relevance_score = excluded.relevance_score,
                    created_at = excluded.created_at
                """,
                (target_id, kol_id, raw_item_id, relevance_score, _utc_now()),
            )

    def list_hotspots(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    h.id,
                    h.score,
                    h.category,
                    h.summary,
                    h.summary_zh,
                    h.summary_en,
                    h.confidence,
                    h.created_at,
                    r.source_type,
                    r.external_id,
                    r.title,
                    r.content,
                    r.author_handle,
                    r.author_followers,
                    r.url,
                    r.published_at,
                    r.engagement
                FROM hotspots h
                INNER JOIN raw_items r ON r.id = h.raw_item_id
                ORDER BY h.score DESC, h.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_monitor_events(
        self, limit: int = 100, target_id: int | None = None
    ) -> list[dict[str, Any]]:
        query = """
            SELECT
                e.id,
                e.target_id,
                t.name AS target_name,
                t.symbol AS target_symbol,
                e.kol_id,
                k.handle AS kol_handle,
                k.followers AS kol_followers,
                e.relevance_score,
                e.created_at,
                r.source_type,
                r.title,
                r.content,
                r.url,
                r.author_handle,
                r.author_followers,
                r.published_at
            FROM monitor_events e
            INNER JOIN watch_targets t ON t.id = e.target_id
            LEFT JOIN kol_accounts k ON k.id = e.kol_id
            INNER JOIN raw_items r ON r.id = e.raw_item_id
        """
        params: list[Any] = []
        if target_id is not None:
            query += " WHERE e.target_id = ?"
            params.append(target_id)
        query += " ORDER BY e.relevance_score DESC, e.created_at DESC LIMIT ?"
        params.append(limit)
        with self._get_conn() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]
