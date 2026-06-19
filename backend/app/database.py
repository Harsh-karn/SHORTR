import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import redis.asyncio as redis

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/urlshortener")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# SQLAlchemy Async Engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Redis Connection Pool
redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
