from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import hashlib
import json
from datetime import datetime, date
import asyncio
from sqlalchemy.future import select

from app.database import AsyncSessionLocal, redis_client
from app.models import APIKey, User

async def update_last_used(key_id):
    async with AsyncSessionLocal() as session:
        key = await session.get(APIKey, key_id)
        if key:
            key.last_used_at = datetime.utcnow()
            await session.commit()

class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only apply to /v1/* routes
        if not request.url.path.startswith("/v1/"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer sk_live_"):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid API key. "
                       "Include 'Authorization: Bearer sk_live_...' in your request."
            )

        raw_key = auth_header.removeprefix("Bearer ")
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        # 1. Try Redis cache
        cached = await redis_client.get(f"apikey:{key_hash}")
        if cached:
            key_data = json.loads(cached)
        else:
            # 2. Fallback to Postgres
            async with AsyncSessionLocal() as session:
                key_record = await session.scalar(
                    select(APIKey).where(
                        APIKey.key_hash == key_hash,
                        APIKey.is_active == True
                    )
                )
                if not key_record:
                    raise HTTPException(status_code=401, detail="Invalid or revoked API key.")

                # key_record.expires_at is naive datetime without timezone or timezone-aware?
                # Usually best to use timezone-aware, but for simplicity here we assume UTC
                if key_record.expires_at and key_record.expires_at.replace(tzinfo=None) < datetime.utcnow():
                    raise HTTPException(status_code=401, detail="This API key has expired.")

                user = await session.get(User, key_record.user_id)
                key_data = {
                    "user_id": str(user.id),
                    "plan": user.plan,
                    "scopes": key_record.scopes,
                    "is_active": True,
                    "key_id": str(key_record.id),
                }

                # Warm cache
                await redis_client.setex(f"apikey:{key_hash}", 300, json.dumps(key_data))

                # Update last_used_at asynchronously (don't block the request)
                asyncio.create_task(update_last_used(key_record.id))

        # 3. Scope check
        required_scope = get_required_scope(request.method, request.url.path)
        if required_scope and required_scope not in key_data["scopes"]:
            raise HTTPException(
                status_code=403,
                detail=f"This API key does not have the '{required_scope}' scope."
            )

        # 4. Rate limiting
        await enforce_rate_limit(request, key_data["key_id"], key_data["plan"])

        # 5. Attach to request state for downstream handlers
        request.state.api_user_id = key_data["user_id"]
        request.state.api_plan = key_data["plan"]
        request.state.api_scopes = key_data["scopes"]

        return await call_next(request)


def get_required_scope(method: str, path: str) -> str | None:
    """Determine required scope based on HTTP method."""
    if method in ("GET", "HEAD"):
        return "read"
    if method in ("POST", "PATCH", "PUT", "DELETE"):
        return "write"
    return None


async def enforce_rate_limit(request: Request, key_id: str, plan: str):
    """Per-plan daily API call limits enforced via Redis counters."""
    daily_limits = {
        "free": 0,
        "pro": 5000,
        "business": 50000,
    }
    limit = daily_limits.get(plan, 0)
    if limit == 0:
        raise HTTPException(
            status_code=403,
            detail="Your plan does not include API access. Upgrade to Pro or Business."
        )

    today = date.today().strftime("%Y%m%d")
    redis_key = f"ratelimit:api:{key_id}:{today}"
    current = await redis_client.incr(redis_key)
    if current == 1:
        await redis_client.expire(redis_key, 90000)  # 25h TTL

    if current > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily API limit of {limit} calls reached. Resets at midnight UTC.",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "midnight UTC",
                "Retry-After": "86400",
            }
        )

    # Attach usage headers to response
    request.state.rate_limit_headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(max(0, limit - current)),
    }
