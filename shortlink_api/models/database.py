import aiosqlite
from pathlib import Path
from typing import Optional

import bcrypt

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

def _row_to_dict(row: aiosqlite.Row) -> dict:
    return dict(row)

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
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            last_used_at TEXT,
            is_active INTEGER DEFAULT 1
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
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active)
    """)
    await db.commit()
    await _init_default_api_key()

async def _init_default_api_key() -> None:
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM api_keys")
    row = await cursor.fetchone()
    if row["cnt"] == 0:
        default_key = settings.DEFAULT_ADMIN_API_KEY
        key_hash = bcrypt.hashpw(default_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        from datetime import datetime, timezone
        created_at = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO api_keys (key_hash, description, created_at, is_active) VALUES (?, ?, ?, 1)",
            (key_hash, "Default Admin API Key", created_at)
        )
        await db.commit()

async def verify_api_key_hash(api_key: str) -> bool:
    db = await get_db()
    cursor = await db.execute(
        "SELECT key_hash FROM api_keys WHERE is_active = 1"
    )
    rows = await cursor.fetchall()
    for row in rows:
        try:
            if bcrypt.checkpw(api_key.encode("utf-8"), row["key_hash"].encode("utf-8")):
                from datetime import datetime, timezone
                await db.execute(
                    "UPDATE api_keys SET last_used_at = ? WHERE key_hash = ?",
                    (datetime.now(timezone.utc).isoformat(), row["key_hash"])
                )
                await db.commit()
                return True
        except Exception:
            continue
    return False

async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None
