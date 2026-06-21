import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional

try:
    from user_agents import parse as parse_ua
    HAS_USER_AGENTS = True
except ImportError:
    HAS_USER_AGENTS = False

from ..core.geoip import lookup_ip
from ..models.database import get_db


def parse_device_type(user_agent: str) -> str:
    if not user_agent:
        return "Unknown"
    
    if HAS_USER_AGENTS:
        try:
            ua = parse_ua(user_agent)
            if ua.is_bot:
                return "Bot"
            elif ua.is_mobile:
                return "Mobile"
            elif ua.is_tablet:
                return "Tablet"
            elif ua.is_pc:
                return "Desktop"
            else:
                return "Other"
        except Exception:
            pass
    
    ua_lower = user_agent.lower()
    if "bot" in ua_lower or "spider" in ua_lower or "crawler" in ua_lower:
        return "Bot"
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        return "Mobile"
    if "tablet" in ua_lower or "ipad" in ua_lower:
        return "Tablet"
    if "windows" in ua_lower or "macintosh" in ua_lower or "linux" in ua_lower:
        return "Desktop"
    return "Other"


async def collect_stats(
    short_code: str,
    ip: str,
    user_agent: str,
    referer: str
) -> None:
    country, city = lookup_ip(ip)
    device_type = parse_device_type(user_agent)
    timestamp = datetime.now(timezone.utc).isoformat()
    
    db = await get_db()
    await db.execute(
        """
        INSERT INTO stats (short_code, ip, user_agent, referer, timestamp, country, city, device_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (short_code, ip, user_agent, referer, timestamp, country, city, device_type)
    )
    await db.execute(
        "UPDATE links SET visit_count = visit_count + 1 WHERE short_code = ?",
        (short_code,)
    )
    await db.commit()
