from fastapi import FastAPI
from app.routers import redirect, links

app = FastAPI(
    title="URL Shortener API",
    description="High performance URL shortener with analytics",
    version="1.0.0",
)

app.include_router(links.router)
app.include_router(redirect.router) # Catch-all /{slug} should be last

@app.get("/health")
async def health_check():
    return {"status": "ok"}
