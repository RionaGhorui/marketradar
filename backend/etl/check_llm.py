import sys
from datetime import datetime, timezone

import openai

from app.config import get_settings
from etl.models import RawItem
from etl.tagger import CONFIG_ERRORS, Tagger


def main() -> int:
    settings = get_settings()
    if not settings.llm_api_key:
        print("LLM_API_KEY is empty. Add it to your .env file and try again.")
        return 1

    client = openai.OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        max_retries=1,
        timeout=30.0,
    )

    try:
        available = sorted(model.id.removeprefix("models/") for model in client.models.list())
    except openai.APIError as error:
        print(f"Could not reach {settings.llm_base_url}: {error}")
        return 1

    print(f"Connected to {settings.llm_base_url}")
    print(f"Models you can use ({len(available)}):")
    for model_id in available:
        print(f"  {model_id}")

    if settings.llm_model not in available:
        print(f"\nLLM_MODEL is '{settings.llm_model}', which is not in that list.")
        print("Copy one chat model name from the list into LLM_MODEL in .env and run this check again.")
        return 1

    sample = RawItem(
        company="Databricks",
        source="check",
        title="Databricks raises $1 billion in a new funding round",
        url="https://example.com/check",
        published_at=datetime.now(timezone.utc),
        text="",
    )
    try:
        tag = Tagger(client, settings.llm_model, requests_per_minute=0).tag(sample)
    except CONFIG_ERRORS as error:
        print(f"\nThe provider rejected the test request: {error}")
        return 1

    if tag is None:
        print("\nThe test request failed or the answer was not readable. Try another LLM_MODEL from the list.")
        return 1

    print(f"\nTest call worked with {settings.llm_model}: {tag.event_type} | {tag.summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
