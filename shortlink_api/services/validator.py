from urllib.parse import urlparse
from typing import Tuple

from ..core.config import settings


def validate_url(url: str) -> Tuple[bool, str]:
    if not url or not isinstance(url, str):
        return False, "URL 不能为空"
    
    if len(url) > 2048:
        return False, "URL 长度不能超过 2048 个字符"
    
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "URL 格式无效"
    
    if not parsed.scheme or parsed.scheme not in ("http", "https"):
        return False, "URL 必须以 http:// 或 https:// 开头"
    
    if not parsed.netloc:
        return False, "URL 格式无效"
    
    domain = parsed.netloc.lower()
    if ":" in domain:
        domain = domain.split(":")[0]
    
    for blacklisted in settings.BLACKLIST_DOMAINS:
        if domain == blacklisted.lower() or domain.endswith("." + blacklisted.lower()):
            return False, "URL 格式无效或域名在黑名单中"
    
    return True, ""


def extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if ":" in domain:
            domain = domain.split(":")[0]
        return domain
    except Exception:
        return ""


def is_custom_code_valid(code: str) -> Tuple[bool, str]:
    if not code or not isinstance(code, str):
        return False, "自定义短码不能为空"
    
    if len(code) < 3 or len(code) > 32:
        return False, "自定义短码长度必须在 3-32 个字符之间"
    
    allowed_chars = set("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-")
    for char in code:
        if char not in allowed_chars:
            return False, "自定义短码只能包含字母、数字、下划线和短横线"
    
    return True, ""
