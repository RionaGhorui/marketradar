from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import openai
import pytest

from etl.models import RawItem
from etl.tagger import Tagger, parse_json_object

REQUEST = httpx.Request("POST", "https://example.test/v1/chat/completions")


class FakeClient:
    def __init__(self, result):
        self.result = result
        self.calls = []
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def reply(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def make_item():
    return RawItem(
        company="Databricks",
        source="Test",
        title="Databricks raises $1B in new funding",
        url="https://example.com/a",
        published_at=datetime(2026, 11, 17, tzinfo=timezone.utc),
        text="Databricks raises $1B in new funding",
    )


def make_tagger(client):
    return Tagger(client, "test-model", requests_per_minute=0)


def test_parse_json_object_handles_code_fences_and_chatter():
    text = 'Sure! ```json\n{"event_type": "funding", "summary": "Raised money."}\n```'
    assert parse_json_object(text) == {"event_type": "funding", "summary": "Raised money."}
    assert parse_json_object("no json here") is None
    assert parse_json_object("{broken json}") is None
    assert parse_json_object(None) is None


def test_tag_returns_event_type_and_summary():
    client = FakeClient(reply('{"event_type": "funding", "summary": "Databricks raised $1B."}'))
    tag = make_tagger(client).tag(make_item())
    assert tag.event_type == "funding"
    assert tag.summary == "Databricks raised $1B."
    assert client.calls[0]["model"] == "test-model"
    assert client.calls[0]["temperature"] == 0


def test_unknown_event_type_falls_back_to_other():
    client = FakeClient(reply('{"event_type": "made_up", "summary": "Something happened."}'))
    assert make_tagger(client).tag(make_item()).event_type == "other"


def test_empty_summary_falls_back_to_title():
    client = FakeClient(reply('{"event_type": "funding", "summary": "  "}'))
    assert make_tagger(client).tag(make_item()).summary == "Databricks raises $1B in new funding"


def test_unreadable_answer_returns_none():
    assert make_tagger(FakeClient(reply("I cannot help with that"))).tag(make_item()) is None
    assert make_tagger(FakeClient(reply(None))).tag(make_item()) is None
    assert make_tagger(FakeClient(SimpleNamespace(choices=[]))).tag(make_item()) is None


def test_temporary_api_error_returns_none():
    client = FakeClient(openai.APIConnectionError(request=REQUEST))
    assert make_tagger(client).tag(make_item()) is None


def test_bad_api_key_is_raised_not_swallowed():
    response = httpx.Response(401, request=REQUEST)
    error = openai.AuthenticationError("invalid api key", response=response, body=None)
    with pytest.raises(openai.AuthenticationError):
        make_tagger(FakeClient(error)).tag(make_item())


def test_requests_are_spaced_out_by_the_rate_limit():
    tagger = Tagger(FakeClient(reply("{}")), "m", requests_per_minute=30)
    assert tagger.min_gap == 2.0
    assert Tagger(FakeClient(reply("{}")), "m", requests_per_minute=0).min_gap == 0.0
