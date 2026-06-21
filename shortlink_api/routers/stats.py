from datetime import datetime, timezone
from typing import Optional, List, Dict
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query

from ..models.schemas import StatsResponse, BatchStatsResponse
from ..models.database import get_db
from ..services.redirector import get_link_by_code
from ..core.geoip import is_geoip_available

router = APIRouter(prefix="/stats", tags=["stats"])


async def _get_stats_for_code(
    short_code: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> StatsResponse:
    link = await get_link_by_code(short_code)
    if link is None:
        raise HTTPException(status_code=404, detail="短链接不存在")
    
    db = await get_db()
    
    query = "SELECT * FROM stats WHERE short_code = ?"
    params = [short_code]
    
    if start:
        try:
            datetime.fromisoformat(start)
            query += " AND timestamp >= ?"
            params.append(start)
        except ValueError:
            raise HTTPException(status_code=400, detail="start 日期格式无效")
    
    if end:
        try:
            datetime.fromisoformat(end)
            query += " AND timestamp <= ?"
            params.append(end)
        except ValueError:
            raise HTTPException(status_code=400, detail="end 日期格式无效")
    
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    
    by_country = defaultdict(int)
    by_device = defaultdict(int)
    timeline = defaultdict(int)
    
    for row in rows:
        country = row["country"] or "Unknown"
        device = row["device_type"] or "Unknown"
        
        by_country[country] += 1
        by_device[device] += 1
        
        try:
            ts = datetime.fromisoformat(row["timestamp"])
            date_str = ts.strftime("%Y-%m-%d")
            timeline[date_str] += 1
        except Exception:
            pass
    
    sorted_timeline = [
        {"date": date, "visits": count}
        for date, count in sorted(timeline.items())
    ]
    
    return StatsResponse(
        short_code=short_code,
        total_visits=len(rows),
        by_country=dict(by_country),
        by_device=dict(by_device),
        timeline=sorted_timeline,
        geoip_available=is_geoip_available(),
    )


@router.get("/batch", response_model=BatchStatsResponse)
async def get_batch_stats(
    codes: str = Query(..., description="短码列表，用逗号分隔"),
    start: Optional[str] = Query(None, description="开始时间 ISO 格式"),
    end: Optional[str] = Query(None, description="结束时间 ISO 格式"),
):
    short_codes = [code.strip() for code in codes.split(",") if code.strip()]
    
    if not short_codes:
        raise HTTPException(status_code=400, detail="请提供至少一个短码")
    
    if len(short_codes) > 100:
        raise HTTPException(status_code=400, detail="最多查询 100 个短码")
    
    geoip_status = is_geoip_available()
    results = {}
    
    for code in short_codes:
        try:
            stats = await _get_stats_for_code(code, start, end)
            results[code] = stats
        except HTTPException as e:
            if e.status_code == 404:
                results[code] = StatsResponse(
                    short_code=code,
                    total_visits=0,
                    by_country={},
                    by_device={},
                    timeline=[],
                    geoip_available=geoip_status,
                )
            else:
                raise
    
    return BatchStatsResponse(results=results)


@router.get("/{short_code}", response_model=StatsResponse)
async def get_stats(
    short_code: str,
    start: Optional[str] = Query(None, description="开始时间 ISO 格式"),
    end: Optional[str] = Query(None, description="结束时间 ISO 格式"),
):
    return await _get_stats_for_code(short_code, start, end)
