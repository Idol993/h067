import os
import threading
import logging
from typing import Optional, Tuple
from pathlib import Path

from ..core.config import settings

logger = logging.getLogger("shortlink")

try:
    import geoip2.database
    import geoip2.errors
    HAS_GEOIP2 = True
except ImportError:
    HAS_GEOIP2 = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

_reader = None
_download_started = False
_download_lock = threading.Lock()


def is_geoip_available() -> bool:
    if not HAS_GEOIP2:
        return False
    if not settings.GEOIP_DB_PATH.exists():
        return False
    reader = _get_reader()
    return reader is not None


def _ensure_db_file() -> bool:
    if settings.GEOIP_DB_PATH.exists() and settings.GEOIP_DB_PATH.stat().st_size > 1000000:
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
        except Exception as e:
            logger.warning(f"GeoIP reader init failed: {e}")
            _reader = None
    return _reader


def _start_download_if_needed():
    global _download_started
    with _download_lock:
        if _download_started:
            return
        if _ensure_db_file():
            return
        _download_started = True
    
    if not HAS_HTTPX:
        logger.warning("httpx not available, skip GeoIP auto-download")
        return
    
    def _do_download():
        try:
            logger.info("Starting GeoLite2-City database download...")
            settings.GEOIP_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = settings.GEOIP_DB_PATH.with_suffix(".mmdb.tmp")
            
            with httpx.stream("GET", settings.GEOIP_DOWNLOAD_URL, follow_redirects=True, timeout=300) as resp:
                resp.raise_for_status()
                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_bytes():
                        f.write(chunk)
            
            if tmp_path.stat().st_size > 1000000:
                os.replace(tmp_path, settings.GEOIP_DB_PATH)
                global _reader
                _reader = None
                logger.info("GeoLite2-City database downloaded successfully")
            else:
                logger.warning("Downloaded file too small, likely not a valid MMDB")
                if tmp_path.exists():
                    os.unlink(tmp_path)
        except Exception as e:
            logger.warning(f"GeoIP download failed: {e}")
            global _download_started
            with _download_lock:
                _download_started = False
    
    threading.Thread(target=_do_download, daemon=True).start()


def lookup_ip(ip: str) -> Tuple[Optional[str], Optional[str]]:
    if not HAS_GEOIP2:
        return None, None
    
    if not _ensure_db_file():
        _start_download_if_needed()
        return None, None
    
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
