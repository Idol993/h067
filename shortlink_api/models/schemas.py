from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict


class LinkCreate(BaseModel):
    url: str = Field(..., description="原始 URL")
    custom_code: Optional[str] = Field(None, description="自定义短码")
    expires_in_days: Optional[int] = Field(None, description="过期天数")
    password: Optional[str] = Field(None, description="访问密码")


class LinkCreateResponse(BaseModel):
    short_code: str
    short_url: str
    created_at: str
    original_url: str
    expires_at: Optional[str] = None
    has_password: bool = False


class LinkInfo(BaseModel):
    id: int
    short_code: str
    original_url: str
    created_at: str
    expires_at: Optional[str] = None
    visit_count: int
    has_password: bool = False


class BatchLinkCreate(BaseModel):
    urls: List[LinkCreate] = Field(..., max_length=100)


class BatchLinkResponse(BaseModel):
    results: List[LinkCreateResponse]


class StatsResponse(BaseModel):
    short_code: str
    total_visits: int
    by_country: Dict[str, int]
    by_device: Dict[str, int]
    timeline: List[Dict[str, object]]


class BatchStatsResponse(BaseModel):
    results: Dict[str, StatsResponse]


class PasswordVerifyRequest(BaseModel):
    password: str


class MessageResponse(BaseModel):
    detail: str
