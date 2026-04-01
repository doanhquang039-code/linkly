from pydantic import BaseModel, HttpUrl

class URLCreate(BaseModel):
    original_url: HttpUrl

class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
