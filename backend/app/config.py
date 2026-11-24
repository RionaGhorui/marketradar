from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://marketradar:marketradar@127.0.0.1:5433/marketradar"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:5500"

    llm_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.3-70b-versatile"
    llm_requests_per_minute: int = 8

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_cache_dir: str | None = None

    raw_data_dir: str = "data/raw"
    lookback_days: int = 14
    max_new_per_company: int = 10
    http_timeout: float = 20.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origin_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
