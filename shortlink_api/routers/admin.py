from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Request, Depends, status

from ..models.schemas import LinkInfo, MessageResponse
from ..models.database import get_db
from ..middleware.auth import verify_admin_api_key
from ..services.redirector import get_link_by_code

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(verify_admin_api_key)])


@router.get("/links", response_model=List[LinkInfo])
async def list_all_links(
    page: int = 1,
    page_size: int = 50,
):
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 200:
        page_size = 50
    
    offset = (page - 1) * page_size
    
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM links ORDER BY id DESC LIMIT ? OFFSET ?",
        (page_size, offset)
    )
    rows = await cursor.fetchall()
    
    result = []
    for row in rows:
        result.append(
            LinkInfo(
                id=row["id"],
                short_code=row["short_code"],
                original_url=row["original_url"],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                visit_count=row["visit_count"],
                has_password=row["password_hash"] is not None,
            )
        )
    
    return result


@router.delete("/links/{short_code}", response_model=MessageResponse)
async def delete_link(short_code: str):
    link = await get_link_by_code(short_code)
    if link is None:
        raise HTTPException(status_code=404, detail="短链接不存在")
    
    db = await get_db()
    await db.execute("DELETE FROM stats WHERE short_code = ?", (short_code,))
    await db.execute("DELETE FROM links WHERE short_code = ?", (short_code,))
    await db.commit()
    
    return MessageResponse(detail="短链接已删除")


@router.get("/stats/summary")
async def get_admin_stats_summary():
    db = await get_db()
    
    cursor = await db.execute("SELECT COUNT(*) as count FROM links")
    row = await cursor.fetchone()
    total_links = row["count"] if row else 0
    
    cursor = await db.execute("SELECT COUNT(*) as count FROM stats")
    row = await cursor.fetchone()
    total_visits = row["count"] if row else 0
    
    cursor = await db.execute(
        "SELECT COUNT(DISTINCT short_code) as count FROM stats"
    )
    row = await cursor.fetchone()
    visited_links = row["count"] if row else 0
    
    return {
        "total_links": total_links,
        "total_visits": total_visits,
        "visited_links": visited_links,
    }
