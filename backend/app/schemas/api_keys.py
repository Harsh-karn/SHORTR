from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

APIScope = Literal["read", "write"]

class APIKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100,
                      description="Human-readable label for this key e.g. 'Zapier Integration'")
    scopes: list[APIScope] = Field(default=["read", "write"],
                                   description="Permissions granted to this key")
    expires_at: Optional[datetime] = Field(None,
                                           description="Optional expiry date. Null = never expires.")

class APIKeyCreateResponse(BaseModel):
    id: UUID
    name: str
    key: str          # Raw key — only returned at creation, never again
    key_prefix: str   # First 10 chars shown in UI forever e.g. "sk_live_ab"
    scopes: list[str]
    created_at: datetime

    class Config:
        from_attributes = True

class APIKeyListItem(BaseModel):
    id: UUID
    name: str
    key_prefix: str   # e.g. "sk_live_ab..." — never the full key
    scopes: list[str]
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class APIKeyRenameRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
