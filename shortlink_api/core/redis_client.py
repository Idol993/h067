from typing import Optional

_redis_client = None
_redis_available = False

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


def init_redis(host: str = "localhost", port: int = 6379, db: int = 0) -> bool:
    global _redis_client, _redis_available
    if not HAS_REDIS:
        return False
    try:
        _redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        _redis_client.ping()
        _redis_available = True
        return True
    except Exception:
        _redis_client = None
        _redis_available = False
        return False


def get_redis():
    return _redis_client if _redis_available else None


def is_redis_available() -> bool:
    return _redis_available


def cache_get(key: str) -> Optional[str]:
    if not _redis_available or _redis_client is None:
        return None
    try:
        return _redis_client.get(key)
    except Exception:
        return None


def cache_set(key: str, value: str, expire_seconds: int = 3600) -> bool:
    if not _redis_available or _redis_client is None:
        return False
    try:
        _redis_client.setex(key, expire_seconds, value)
        return True
    except Exception:
        return False


def cache_delete(key: str) -> bool:
    if not _redis_available or _redis_client is None:
        return False
    try:
        _redis_client.delete(key)
        return True
    except Exception:
        return False
