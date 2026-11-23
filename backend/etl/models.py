from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class RawItem:
    company: str
    source: str
    title: str
    url: str
    published_at: datetime | None
    text: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["published_at"] = self.published_at.isoformat() if self.published_at else None
        return data


@dataclass
class Tag:
    event_type: str
    summary: str
