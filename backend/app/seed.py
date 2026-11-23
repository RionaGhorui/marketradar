from psycopg_pool import ConnectionPool

TRACKED_COMPANIES = [
    ("Databricks", "https://www.databricks.com", "Databricks", "https://www.databricks.com/feed"),
    ("Snowflake", "https://www.snowflake.com", "Snowflake data cloud", None),
    ("OpenAI", "https://openai.com", "OpenAI", "https://openai.com/news/rss.xml"),
    ("Anthropic", "https://www.anthropic.com", "Anthropic Claude", None),
    ("Cohere", "https://cohere.com", "Cohere AI", None),
    ("Mistral AI", "https://mistral.ai", "Mistral AI", None),
    ("Hugging Face", "https://huggingface.co", "Hugging Face", "https://huggingface.co/blog/feed.xml"),
    ("Pinecone", "https://www.pinecone.io", "Pinecone vector database", None),
]

UPSERT_COMPANY = """
INSERT INTO tracked_companies (name, website, news_query, blog_feed)
VALUES (%s, %s, %s, %s)
ON CONFLICT (name) DO UPDATE
SET website = EXCLUDED.website,
    news_query = EXCLUDED.news_query,
    blog_feed = EXCLUDED.blog_feed
"""


def seed_companies(pool: ConnectionPool) -> None:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_COMPANY, TRACKED_COMPANIES)
