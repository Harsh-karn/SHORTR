from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routers import redirect, links, api_keys
from app.services.analytics import init_clickhouse
from app.middleware.api_auth import APIKeyAuthMiddleware
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_clickhouse()
    yield

app = FastAPI(
    title="URL Shortener API",
    description="High performance URL shortener with analytics",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(APIKeyAuthMiddleware)

app.include_router(links.router)
app.include_router(api_keys.router)
app.include_router(redirect.router) # Catch-all /{slug} should be last

@app.get("/health")
async def health_check():
    return {"status": "ok"}
