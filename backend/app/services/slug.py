import nanoid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Link
import redis.asyncio as redis

ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

def generate_slug(length: int = 7) -> str:
    return nanoid.generate(ALPHABET, length)

async def generate_unique_slug(db: AsyncSession, redis_client: redis.Redis, length: int = 7) -> str:
    for _ in range(10):
        slug = generate_slug(length)
        
        # Check Redis
        redis_exists = await redis_client.exists(f"link:{slug}")
        if redis_exists:
            continue
            
        # Check DB
        result = await db.execute(select(Link).filter(Link.slug == slug))
        if result.scalar_one_or_none():
            continue
            
        return slug
        
    # fallback to longer slug
    return generate_slug(length + 1)
