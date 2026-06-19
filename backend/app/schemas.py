from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class LinkCreate(BaseModel):
    destination_url: HttpUrl
    slug: Optional[str] = Field(default=None, min_length=3, max_length=50)
    title: Optional[str] = None
    domain_id: Optional[UUID] = None
    has_analytics: bool = False
    expires_at: Optional[datetime] = None
    password: Optional[str] = None

class LinkResponse(BaseModel):
    id: UUID
    slug: str
    destination_url: HttpUrl
    title: Optional[str]
    domain_id: Optional[UUID]
    is_active: bool
    has_analytics: bool
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
