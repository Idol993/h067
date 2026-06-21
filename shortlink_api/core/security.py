import hmac
import hashlib
import base64
import json
import time
from typing import Optional, Tuple

from ..core.config import settings

def _sign(data: str) -> str:
    mac = hmac.new(
        settings.COOKIE_SECRET_KEY.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256
    )
    return base64.urlsafe_b64encode(mac.digest()).decode("ascii").rstrip("=")

def generate_signed_cookie(short_code: str, ttl_seconds: int = None) -> str:
    if ttl_seconds is None:
        ttl_seconds = settings.PASSWORD_COOKIE_TTL
    
    expires_at = int(time.time()) + ttl_seconds
    payload = json.dumps({
        "sc": short_code,
        "exp": expires_at,
    }, separators=(",", ":"))
    
    payload_b64 = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    signature = _sign(payload_b64)
    
    return f"{payload_b64}.{signature}"

def verify_signed_cookie(cookie_value: str) -> Tuple[bool, Optional[str]]:
    if not cookie_value or "." not in cookie_value:
        return False, None
    
    try:
        payload_b64, signature = cookie_value.rsplit(".", 1)
    except ValueError:
        return False, None
    
    expected_signature = _sign(payload_b64)
    if not hmac.compare_digest(signature, expected_signature):
        return False, None
    
    try:
        padding = 4 - (len(payload_b64) % 4)
        if padding != 4:
            payload_b64 += "=" * padding
        payload_json = base64.urlsafe_b64decode(payload_b64.encode("ascii")).decode("utf-8")
        payload = json.loads(payload_json)
    except Exception:
        return False, None
    
    if "exp" not in payload or "sc" not in payload:
        return False, None
    
    if int(payload["exp"]) < int(time.time()):
        return False, None
    
    return True, payload["sc"]
