from datetime import datetime

from pydantic import BaseModel, Field


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


class SearchHitOut(ArticleOut):
    score: float


class HeadlineOut(BaseModel):
    title: str
    url: str
    event_type: str | None = None
    summary: str | None = None
    published_at: datetime | None = None


class BriefingCompanyOut(BaseModel):
    company: str
    total: int
    by_type: dict[str, int]
    headlines: list[HeadlineOut]


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    company: str | None = None
    event_type: str | None = None
    days: int | None = Field(default=None, ge=1, le=365)


class SourceOut(BaseModel):
    number: int
    title: str
    url: str
    company: str
    source: str | None = None
    published_at: str | None = None
    event_type: str | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
