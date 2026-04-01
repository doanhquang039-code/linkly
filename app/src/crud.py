import shortuuid
import redis.asyncio as redis
from sqlalchemy import text
from .database import engine

async def create_short_url(original_url: str, redis_client: redis.Redis) -> str:
    short_code = shortuuid.uuid()[:8]
    
    # Lưu vào Redis trước
    await redis_client.set(short_code, str(original_url), ex=86400*30)  # 30 ngày
    
    # Lưu vào PostgreSQL
    async with engine.begin() as conn:
        await conn.execute(
            text("""INSERT INTO urls (short_code, original_url) 
                    VALUES (:code, :url) 
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
