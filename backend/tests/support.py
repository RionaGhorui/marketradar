from app.embeddings import vector_literal

DIMENSIONS = 384


def unit_vector(index: int) -> list[float]:
    values = [0.0] * DIMENSIONS
    values[index] = 1.0
    return values


class FakeEmbedder:
    def __init__(self, index: int = 0):
        self.index = index

    def embed(self, texts):
        return [unit_vector(self.index) for _ in texts]


def add_article(
    pool,
    company,
    title,
    url,
    event_type="funding",
    minutes_ago=10,
    summary="A short summary",
    vector_index=None,
):
    embedding = vector_literal(unit_vector(vector_index)) if vector_index is not None else None
    with pool.connection() as conn:
        company_id = conn.execute(
            "SELECT id FROM tracked_companies WHERE name = %s", (company,)
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO articles "
            "(url, title, source, published_at, company_id, event_type, summary, embedding) "
            "VALUES (%s, %s, 'Test', now() - make_interval(mins => %s), %s, %s, %s, %s::vector)",
            (url, title, minutes_ago, company_id, event_type, summary, embedding),
        )
