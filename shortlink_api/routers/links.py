from datetime import datetime, timezone, timedelta
from typing import List

from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import JSONResponse

from ..models.schemas import (
    LinkCreate,
    LinkCreateResponse,
    LinkInfo,
    BatchLinkCreate,
    BatchLinkResponse,
    MessageResponse,
)
from ..services.shortcode import generate_short_code
from ..services.validator import validate_url, is_custom_code_valid
from ..services.redirector import hash_password, get_link_by_code
from ..models.database import get_db
from ..core.config import settings
from ..core.rate_limiter import limiter

router = APIRouter(prefix="/links", tags=["links"])


@router.post("", response_model=LinkCreateResponse)
@limiter.limit(settings.RATE_LIMIT_CREATE)
async def create_link(request: Request, link_data: LinkCreate):
    is_valid, error_msg = validate_url(link_data.url)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    db = await get_db()
    
    short_code = None
    is_custom = False
    
    if link_data.custom_code:
        is_valid_code, code_error = is_custom_code_valid(link_data.custom_code)
        if not is_valid_code:
            raise HTTPException(status_code=400, detail=code_error)
        
        existing = await get_link_by_code(link_data.custom_code)
        if existing:
            raise HTTPException(
                status_code=409,
                detail="自定义短码已被占用，请换一个"
            )
        
        short_code = link_data.custom_code
        is_custom = True
    else:
        while True:
            short_code = generate_short_code()
            existing = await get_link_by_code(short_code)
            if not existing:
                break
    
    created_at = datetime.now(timezone.utc).isoformat()
    
    expires_at = None
    if link_data.expires_in_days and link_data.expires_in_days > 0:
        expires_at = (
            datetime.now(timezone.utc) + timedelta(days=link_data.expires_in_days)
        ).isoformat()
    
    password_hash = None
    if link_data.password:
        password_hash = hash_password(link_data.password)
    
    await db.execute(
        """
        INSERT INTO links (short_code, original_url, custom_code, created_at, expires_at, password_hash, visit_count)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        (short_code, link_data.url, 1 if is_custom else 0, created_at, expires_at, password_hash)
    )
    await db.commit()
    
    return LinkCreateResponse(
        short_code=short_code,
        short_url=f"{settings.BASE_URL}/{short_code}",
        created_at=created_at,
        original_url=link_data.url,
        expires_at=expires_at,
        has_password=password_hash is not None,
    )


@router.post("/batch", response_model=BatchLinkResponse)
@limiter.limit(settings.RATE_LIMIT_CREATE)
async def create_batch_links(request: Request, batch_data: BatchLinkCreate):
    if len(batch_data.urls) > settings.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"批量创建最多 {settings.MAX_BATCH_SIZE} 个"
        )
    
    results = []
    
    for link_data in batch_data.urls:
        try:
            result = await create_link(request, link_data)
            results.append(result)
        except HTTPException as e:
            results.append({
                "short_code": None,
                "short_url": None,
                "created_at": None,
                "original_url": link_data.url,
                "error": e.detail,
            })
    
    return BatchLinkResponse(results=results)


@router.get("/{short_code}", response_model=LinkInfo)
async def get_link_info(short_code: str):
    link = await get_link_by_code(short_code)
    
    if link is None:
        raise HTTPException(status_code=404, detail="短链接不存在")
    
    return LinkInfo(
        id=link["id"],
        short_code=link["short_code"],
        original_url=link["original_url"],
        created_at=link["created_at"],
        expires_at=link["expires_at"],
        visit_count=link["visit_count"],
        has_password=link.get("password_hash") is not None,
    )
