from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from slowapi import Limiter
from slowapi.util import get_remote_address
import redis.asyncio as redis
import os
from . import schemas, crud
from .database import engine
from .models import Base

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully!")
    yield
    await engine.dispose()

app = FastAPI(title="Linkly - URL Shortener", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "linkly"}

@app.post("/shorten", response_model=schemas.ShortenResponse)
@limiter.limit("10/minute")
async def shorten_url(request: Request, url: schemas.URLCreate):
    """Create short URL"""
    short_code = await crud.create_short_url(str(url.original_url), redis_client)
    base_url = os.getenv("BASE_URL", "http://localhost")
    return schemas.ShortenResponse(
        short_code=short_code,
        short_url=f"{base_url}/{short_code}"
    )

@app.get("/{short_code}")
async def redirect_url(short_code: str):
    """Redirect to original URL"""
    original_url = await crud.get_original_url(short_code, redis_client)
    if not original_url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    
    await crud.increment_clicks(short_code, redis_client)
    return RedirectResponse(url=original_url, status_code=302)
