from psycopg_pool import ConnectionPool

TRACKED_COMPANIES = [
    ("Databricks", "https://www.databricks.com", "Databricks"),
    ("Snowflake", "https://www.snowflake.com", "Snowflake data cloud"),
    ("OpenAI", "https://openai.com", "OpenAI"),
    ("Anthropic", "https://www.anthropic.com", "Anthropic Claude"),
    ("Cohere", "https://cohere.com", "Cohere AI"),
    ("Mistral AI", "https://mistral.ai", "Mistral AI"),
    ("Hugging Face", "https://huggingface.co", "Hugging Face"),
    ("Pinecone", "https://www.pinecone.io", "Pinecone vector database"),
]


def seed_companies(pool: ConnectionPool) -> None:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO tracked_companies (name, website, news_query) "
                "VALUES (%s, %s, %s) ON CONFLICT (name) DO NOTHING",
                TRACKED_COMPANIES,
            )
