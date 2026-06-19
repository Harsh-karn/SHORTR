from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from uuid import UUID
import hashlib, secrets, json

from app.database import get_db, redis_client
from app.auth import get_current_user   # Clerk JWT validation for dashboard users
from app.models import APIKey, User
from app.schemas.api_keys import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyListItem,
    APIKeyRenameRequest,
)

router = APIRouter(prefix="/api-keys", tags=["API Keys"])

def generate_api_key() -> tuple[str, str, str]:
    """Returns (raw_key, key_prefix, key_hash)"""
    random_part = secrets.token_urlsafe(24)       # 32 URL-safe chars
    raw_key = f"sk_live_{random_part}"
    key_prefix = raw_key[:10]                      # "sk_live_ab" shown in UI
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_prefix, key_hash

@router.post("", response_model=APIKeyCreateResponse, status_code=201)
async def create_api_key(
    body: APIKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a new API key for the authenticated dashboard user.
    The raw key is returned ONCE and never stored — only its hash is saved.
    """
    # Enforce per-plan key limits
    existing_count = await db.scalar(
        select(func.count()).where(
            APIKey.user_id == current_user.id,
            APIKey.is_active == True
        )
    )
    plan_limits = {"free": 0, "pro": 3, "business": 10}
    if existing_count >= plan_limits.get(current_user.plan, 0):
        raise HTTPException(
            status_code=403,
            detail=f"Your {current_user.plan} plan allows a maximum of "
                   f"{plan_limits.get(current_user.plan, 0)} active API keys. "
                   f"Upgrade to create more."
        )

    raw_key, key_prefix, key_hash = generate_api_key()

    api_key = APIKey(
        user_id=current_user.id,
        name=body.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=body.scopes or ["read", "write"],
        expires_at=body.expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    # Warm Redis cache immediately
    await redis_client.setex(
        f"apikey:{key_hash}",
        300,  # 5 min TTL
        json.dumps({
            "user_id": str(current_user.id),
            "plan": current_user.plan,
            "scopes": api_key.scopes,
            "is_active": True,
            "key_id": str(api_key.id),
        })
    )

    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,          # ONLY time raw key is returned
        key_prefix=key_prefix,
        scopes=api_key.scopes,
        created_at=api_key.created_at,
    )


@router.get("", response_model=list[APIKeyListItem])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active API keys for the user. Raw key is never returned here."""
    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == current_user.id, APIKey.is_active == True)
        .order_by(APIKey.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/{key_id}/rename")
async def rename_api_key(
    key_id: UUID,
    body: APIKeyRenameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    key = await db.get(APIKey, key_id)
    if not key or key.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="API key not found")
    key.name = body.name
    await db.commit()
    return {"success": True}


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete the key. Invalidates Redis cache immediately."""
    key = await db.get(APIKey, key_id)
    if not key or key.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="API key not found")

    key.is_active = False
    await db.commit()

    # Bust Redis cache so the key stops working immediately
    await redis_client.delete(f"apikey:{key.key_hash}")
