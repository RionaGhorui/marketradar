CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS tracked_companies (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    website TEXT,
    news_query TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE tracked_companies ADD COLUMN IF NOT EXISTS blog_feed TEXT;

CREATE TABLE IF NOT EXISTS articles (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source TEXT,
    published_at TIMESTAMPTZ,
    content TEXT,
    company_id INTEGER REFERENCES tracked_companies (id),
    event_type TEXT,
    summary TEXT,
    embedding vector(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector(
            'english',
            coalesce(title, '') || ' ' || coalesce(summary, '') || ' ' || coalesce(content, '')
        )
    ) STORED
);

CREATE INDEX IF NOT EXISTS articles_search_idx ON articles USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS articles_embedding_idx ON articles USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS articles_company_date_idx ON articles (company_id, published_at DESC);
