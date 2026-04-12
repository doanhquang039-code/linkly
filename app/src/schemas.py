from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime

class URLCreate(BaseModel):
    original_url: HttpUrl
    custom_code: Optional[str] = Field(None, min_length=3, max_length=20)

class ShortenResponse(BaseModel):
    short_code: str
    short_url: str

class URLStats(BaseModel):
    short_code: str
    original_url: str
    clicks: int
    created_at: datetime

class URLListResponse(BaseModel):
    links: List[URLStats]
