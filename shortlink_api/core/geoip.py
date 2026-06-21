import os
from typing import Optional, Tuple
from pathlib import Path

from ..core.config import settings

try:
    import geoip2.database
    import geoip2.errors
    HAS_GEOIP2 = True
except ImportError:
    HAS_GEOIP2 = False

_reader = None


def _ensure_db_file() -> bool:
    if settings.GEOIP_DB_PATH.exists():
        return True
    return False


def _get_reader():
    global _reader
    if _reader is None:
        if not HAS_GEOIP2:
            return None
        if not _ensure_db_file():
            return None
        try:
            _reader = geoip2.database.Reader(str(settings.GEOIP_DB_PATH))
        except Exception:
            _reader = None
    return _reader


def lookup_ip(ip: str) -> Tuple[Optional[str], Optional[str]]:
    if not ip or ip in ("127.0.0.1", "localhost", "::1"):
        return None, None
    
    reader = _get_reader()
    if reader is None:
        return None, None
    
    try:
        response = reader.city(ip)
        country = response.country.iso_code if response.country else None
        city = response.city.name if response.city else None
        return country, city
    except Exception:
        return None, None


def close_reader():
    global _reader
    if _reader is not None:
        try:
            _reader.close()
        except Exception:
            pass
        _reader = None
