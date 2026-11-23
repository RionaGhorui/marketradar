import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone

from etl import loader
from etl.clean import clean_items
from etl.models import RawItem

log = logging.getLogger(__name__)

MAX_FAILURES_IN_A_ROW = 5


class Pipeline:
    def __init__(self, pool, fetch, tagger, embedder, raw_store, lookback_days=14, max_new_per_company=10):
        self.pool = pool
        self.fetch = fetch
        self.tagger = tagger
        self.embedder = embedder
        self.raw_store = raw_store
        self.lookback_days = lookback_days
        self.max_new_per_company = max_new_per_company
        self.failures_in_a_row = 0

    def run(self) -> Counter:
        now = datetime.now(timezone.utc)
        stats: Counter = Counter()

        companies = loader.load_companies(self.pool)
        company_ids = {company["name"]: company["id"] for company in companies}

        fetched, failures = self.fetch(companies)
        stats["fetched"] = len(fetched)
        stats["fetch_failures"] = failures
        if fetched:
            path = self.raw_store.save(fetched, now)
            log.info("saved %d raw items to %s", len(fetched), path)

        items, clean_stats = clean_items(fetched, now, self.lookback_days)
        stats.update(clean_stats)

        known_urls = loader.find_existing_urls(self.pool, [item.url for item in items])
        fresh = [item for item in items if item.url not in known_urls]
        stats["already_in_database"] = len(items) - len(fresh)

        by_company: dict[str, list[RawItem]] = defaultdict(list)
        for item in fresh:
            by_company[item.company].append(item)

        for name, company_items in by_company.items():
            if name not in company_ids:
                stats["unknown_company"] += len(company_items)
                continue
            newest_first = sorted(company_items, key=lambda i: i.published_at, reverse=True)
            chosen = newest_first[: self.max_new_per_company]
            stats["skipped_over_cap"] += len(newest_first) - len(chosen)
            keep_going = self.process_company(name, company_ids[name], chosen, stats)
            if not keep_going:
                log.warning("stopping early, the language model keeps failing (daily limit reached?)")
                break

        log.info("pipeline finished: %s", dict(stats))
        return stats

    def process_company(self, name: str, company_id: int, items: list[RawItem], stats: Counter) -> bool:
        rows = []
        keep_going = True

        for item in items:
            tag = self.tagger.tag(item)
            if tag is None:
                stats["tag_failed"] += 1
                self.failures_in_a_row += 1
                if self.failures_in_a_row >= MAX_FAILURES_IN_A_ROW:
                    stats["stopped_early"] = 1
                    keep_going = False
                    break
                continue

            self.failures_in_a_row = 0
            if tag.event_type == "irrelevant":
                stats["irrelevant"] += 1
            rows.append(
                {
                    "url": item.url,
                    "title": item.title,
                    "source": item.source,
                    "published_at": item.published_at,
                    "content": item.text,
                    "company_id": company_id,
                    "event_type": tag.event_type,
                    "summary": tag.summary,
                    "embedding": None,
                }
            )

        relevant = [row for row in rows if row["event_type"] != "irrelevant"]
        if relevant:
            vectors = self.embedder.embed([f"{row['title']}. {row['summary']}" for row in relevant])
            for row, vector in zip(relevant, vectors):
                row["embedding"] = vector

        loaded = loader.insert_articles(self.pool, rows)
        stats["loaded"] += loaded
        log.info("%s: tagged %d, stored %d", name, len(rows), loaded)
        return keep_going
