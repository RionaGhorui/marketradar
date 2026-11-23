import json
from datetime import datetime
from pathlib import Path

from etl.models import RawItem


class LocalRawStore:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)

    def save(self, items: list[RawItem], run_time: datetime) -> Path:
        folder = self.base_dir / run_time.strftime("%Y-%m-%d")
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{run_time.strftime('%H%M%S')}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for item in items:
                handle.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")
        return path
