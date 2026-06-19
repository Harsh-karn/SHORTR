import json
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import redis.asyncio as redis

from app.database import get_db, redis_client
from app.models import Link
from app.workers.tasks import record_click

router = APIRouter()

@router.get("/{slug}")
async def redirect_slug(
    slug: str, 
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # 1. Check Redis Cache
    cache_key = f"link:{slug}"
    cached_data = await redis_client.get(cache_key)
    
    if cached_data:
        link_data = json.loads(cached_data)
    else:
        # 2. On Cache Miss: Query DB
        result = await db.execute(select(Link).filter(Link.slug == slug))
        link = result.scalar_one_or_none()
        
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
            
        link_data = {
            "destination_url": link.destination_url,
            "is_active": link.is_active,
            "has_analytics": link.has_analytics,
            "link_id": str(link.id)
        }
        
        # Warm Redis Cache (24h TTL)
        await redis_client.set(cache_key, json.dumps(link_data), ex=86400)
    
    # 3. Check active status
    if not link_data["is_active"]:
        raise HTTPException(status_code=404, detail="Link is inactive")
        
    # 4. Handle Analytics (push to celery worker)
    if link_data["has_analytics"]:
        metadata = {
            "ip": request.client.host,
            "user_agent": request.headers.get("user-agent", ""),
            "referrer": request.headers.get("referer", "")
        }
        # Call celery task asynchronously
        record_click.delay(
            link_id=link_data["link_id"],
            slug=slug,
            user_id="", # User ID of clicker not known unless authenticated
            request_metadata=metadata
        )
        
    # 5. Redirect
    return RedirectResponse(url=link_data["destination_url"], status_code=302)
