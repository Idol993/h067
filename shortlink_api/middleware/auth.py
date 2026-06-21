from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader

from ..models.database import verify_api_key_hash

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_admin_api_key(request: Request) -> bool:
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key"
        )
    
    is_valid = await verify_api_key_hash(api_key)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无效的 API Key"
        )
    
    return True
