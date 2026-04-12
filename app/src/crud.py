import shortuuid
import redis.asyncio as redis
from sqlalchemy import text
from .database import engine
from datetime import datetime

async def create_short_url(original_url: str, redis_client: redis.Redis, custom_code: str = None) -> str:
    short_code = custom_code or shortuuid.uuid()[:8]
    
    await redis_client.set(short_code, str(original_url), ex=86400*30)
    
    async with engine.begin() as conn:
        await conn.execute(
            text("""INSERT INTO urls (short_code, original_url, clicks) 
                    VALUES (:code, :url, 0) 
                    ON CONFLICT (short_code) DO NOTHING"""),
            {"code": short_code, "url": str(original_url)}
        )
    return short_code

async def get_original_url(short_code: str, redis_client: redis.Redis):
    url = await redis_client.get(short_code)
    if url:
        return url.decode('utf-8')
    
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT original_url FROM urls WHERE short_code = :code"),
            {"code": short_code}
        )
        row = result.fetchone()
        if row:
            url = row[0]
            await redis_client.set(short_code, url, ex=86400*30)
            return url
    return None

async def increment_clicks(short_code: str, redis_client: redis.Redis):
    await redis_client.incr(f"clicks:{short_code}")
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE urls SET clicks = clicks + 1 WHERE short_code = :code"),
            {"code": short_code}
        )

async def get_url_stats(short_code: str):
    async with engine.begin() as conn:
        result = await conn.execute(
            text("""SELECT short_code, original_url, clicks, created_at 
                    FROM urls WHERE short_code = :code"""),
            {"code": short_code}
        )
        row = result.fetchone()
        if row:
            return {
                "short_code": row[0],
                "original_url": row[1],
                "clicks": row[2],
                "created_at": row[3]
            }
    return None

async def get_all_links():
    async with engine.begin() as conn:
        result = await conn.execute(
            text("""SELECT short_code, original_url, clicks, created_at 
                    FROM urls ORDER BY created_at DESC""")
        )
        rows = result.fetchall()
        return [
            {
                "short_code": row[0],
                "original_url": row[1],
                "clicks": row[2],
                "created_at": row[3]
            } for row in rows
        ]

async def delete_link(short_code: str, redis_client: redis.Redis):
    # Xóa trong Redis
    await redis_client.delete(short_code)
    await redis_client.delete(f"clicks:{short_code}")
    
    # Xóa trong DB
    async with engine.begin() as conn:
        result = await conn.execute(
            text("DELETE FROM urls WHERE short_code = :code"),
            {"code": short_code}
        )
        return result.rowcount > 0
