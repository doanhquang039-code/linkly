from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from contextlib import asynccontextmanager
from slowapi import Limiter
from slowapi.util import get_remote_address
import redis.asyncio as redis
import os
from . import schemas, crud
from .database import engine
from .models import Base
from .chatbot import chatbot_response

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
    return {"status": "healthy", "service": "linkly"}

@app.post("/shorten", response_model=schemas.ShortenResponse)
@limiter.limit("10/minute")
async def shorten_url(request: Request, url: schemas.URLCreate):
    short_code = await crud.create_short_url(
        str(url.original_url), 
        redis_client, 
        url.custom_code
    )
    base_url = os.getenv("BASE_URL", "http://localhost")
    return schemas.ShortenResponse(
        short_code=short_code,
        short_url=f"{base_url}/{short_code}"
    )

@app.get("/{short_code}")
async def redirect_url(short_code: str):
    original_url = await crud.get_original_url(short_code, redis_client)
    if not original_url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    
    await crud.increment_clicks(short_code, redis_client)
    return RedirectResponse(url=original_url, status_code=302)

@app.get("/stats/{short_code}")
async def get_stats(short_code: str):
    stats = await crud.get_url_stats(short_code)
    if not stats:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return stats

@app.get("/links")
async def get_all_links():
    links = await crud.get_all_links()
    return {"links": links}

@app.delete("/links/{short_code}")
async def delete_link(short_code: str):
    deleted = await crud.delete_link(short_code, redis_client)
    if not deleted:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return {"message": f"Link {short_code} deleted successfully"}

@app.post("/chat")
async def chat_with_bot(message: dict):
    user_message = message.get("message", "")
    if not user_message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    response = await chatbot_response(user_message, redis_client)
    return {"response": response}
