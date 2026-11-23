from datetime import datetime

from pydantic import BaseModel


class CompanyOut(BaseModel):
    id: int
    name: str
    website: str | None = None


class ArticleOut(BaseModel):
    id: int
    company: str
    title: str
    url: str
    source: str | None = None
    published_at: datetime | None = None
    event_type: str | None = None
    summary: str | None = None
