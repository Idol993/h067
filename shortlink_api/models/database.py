import aiosqlite
from pathlib import Path
from typing import Optional

from ..core.config import settings

_db: Optional[aiosqlite.Connection] = None

async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        settings.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(str(settings.DATABASE_PATH))
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await _init_tables()
    return _db

async def _init_tables() -> None:
    db = await get_db()
    await db.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            custom_code INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            password_hash TEXT,
            visit_count INTEGER DEFAULT 0
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT NOT NULL,
            ip TEXT,
            user_agent TEXT,
            referer TEXT,
            timestamp TEXT NOT NULL,
            country TEXT,
            city TEXT,
            device_type TEXT,
            FOREIGN KEY (short_code) REFERENCES links(short_code)
        )
    """)
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_stats_short_code ON stats(short_code)
    """)
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_stats_timestamp ON stats(timestamp)
    """)
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_links_short_code ON links(short_code)
    """)
    await db.commit()

async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None
