from datetime import datetime, timezone
from typing import Optional, Tuple

import bcrypt

from ..models.database import get_db
from .stats_collector import collect_stats


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


async def get_link_by_code(short_code: str) -> Optional[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM links WHERE short_code = ?",
        (short_code,)
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


def is_link_expired(link: dict) -> bool:
    expires_at = link.get("expires_at")
    if expires_at is None:
        return False
    try:
        expire_time = datetime.fromisoformat(expires_at)
        return datetime.now(timezone.utc) > expire_time
    except Exception:
        return False


async def handle_redirect(
    short_code: str,
    ip: str,
    user_agent: str,
    referer: str,
    permanent: bool = False
) -> Tuple[int, Optional[str], Optional[str]]:
    link = await get_link_by_code(short_code)
    
    if link is None:
        return 404, None, None
    
    if is_link_expired(link):
        return 410, None, None
    
    status_code = 301 if permanent else 302
    
    await collect_stats(short_code, ip, user_agent, referer)
    
    return status_code, link["original_url"], link.get("password_hash")


async def verify_link_password(short_code: str, password: str) -> bool:
    link = await get_link_by_code(short_code)
    if link is None:
        return False
    
    password_hash = link.get("password_hash")
    if not password_hash:
        return True
    
    return verify_password(password, password_hash)
