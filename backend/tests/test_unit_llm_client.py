"""Unit tests for LLMClient response normalization. No network."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.utils.llm_client import LLMClient


class _FakeCompletions:
    def __init__(self, content):
        self.content = content

    def create(self, **_kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.content)
                )
            ],
            usage=None,
        )


class _FakeClient:
    def __init__(self, content):
        self.chat = SimpleNamespace(completions=_FakeCompletions(content))


def _client_for(content):
    client = LLMClient.__new__(LLMClient)
    client.api_key = "test-key"
    client.base_url = "https://example.test/v1"
    client.model = "test-model"
    client._num_ctx = 8192
    client.client = _FakeClient(content)
    return client


def test_chat_returns_cleaned_string_content():
    client = _client_for(" hello ")

    assert client.chat([{"role": "user", "content": "hi"}]) == "hello"


def test_chat_strips_think_blocks():
    client = _client_for("<think>hidden reasoning</think>\nvisible answer")

    assert client.chat([{"role": "user", "content": "hi"}]) == "visible answer"


def test_chat_returns_none_for_null_content():
    client = _client_for(None)

    assert client.chat([{"role": "user", "content": "hi"}]) is None


def test_chat_joins_list_text_blocks():
    client = _client_for([
        {"type": "text", "text": "hello"},
        SimpleNamespace(text=" world"),
        {"type": "image_url", "image_url": {"url": "ignored"}},
    ])

    assert client.chat([{"role": "user", "content": "hi"}]) == "hello world"


def test_chat_json_empty_response_raises_clear_error():
    client = _client_for(None)

    with pytest.raises(ValueError, match="LLM returned empty response"):
        client.chat_json([{"role": "user", "content": "json please"}])
