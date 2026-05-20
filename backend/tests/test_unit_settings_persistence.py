"""Unit coverage for Settings preset and dotenv persistence helpers."""

from __future__ import annotations

from app.api import settings as settings_api
from app.config import Config


def test_replace_env_lines_cleans_inline_placeholder_key_comments():
    existing = (
        "LLM_API_KEY=                          # paste your OpenRouter key\n"
        "SMART_API_KEY=                        # same key\n"
        "LLM_PROVIDER=claude-code\n"
    )

    rendered = settings_api._replace_env_lines(
        existing,
        {
            "LLM_API_KEY": "",
            "SMART_API_KEY": "sk value # with hash",
            "LLM_PROVIDER": "openai",
        },
    )

    assert "LLM_API_KEY=\n" in rendered
    assert "LLM_API_KEY=                          #" not in rendered
    assert 'SMART_API_KEY="sk value # with hash"\n' in rendered
    assert "LLM_PROVIDER=openai\n" in rendered


def test_replace_env_lines_appends_missing_runtime_keys_once():
    existing = "LLM_PROVIDER=claude-code\n"
    values = {
        "LLM_PROVIDER": "openai",
        "WONDERWALL_BASE_URL": "https://openrouter.ai/api/v1",
        "WONDERWALL_API_KEY": "",
        "EMBEDDING_DIMENSIONS": 768,
    }

    rendered = settings_api._replace_env_lines(existing, values)
    rendered_again = settings_api._replace_env_lines(rendered, values)

    assert "LLM_PROVIDER=openai\n" in rendered
    assert "WONDERWALL_BASE_URL=https://openrouter.ai/api/v1\n" in rendered
    assert "WONDERWALL_API_KEY=\n" in rendered
    assert "EMBEDDING_DIMENSIONS=768\n" in rendered
    assert rendered_again.count("# Runtime settings persisted by the Settings page") == 1


def test_cheap_preset_sets_cloud_models_and_all_key_slots():
    attrs = [
        "LLM_PROVIDER",
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_MODEL_NAME",
        "SMART_PROVIDER",
        "SMART_API_KEY",
        "SMART_BASE_URL",
        "SMART_MODEL_NAME",
        "NER_API_KEY",
        "NER_BASE_URL",
        "NER_MODEL_NAME",
        "WONDERWALL_MODEL_NAME",
        "WONDERWALL_BASE_URL",
        "WONDERWALL_API_KEY",
        "EMBEDDING_PROVIDER",
        "EMBEDDING_MODEL",
        "EMBEDDING_BASE_URL",
        "EMBEDDING_API_KEY",
        "EMBEDDING_DIMENSIONS",
        "WEB_SEARCH_MODEL",
    ]
    snapshot = {attr: getattr(Config, attr) for attr in attrs}

    try:
        settings_api._apply_preset("cheap", "sk-or-v1-test")

        assert Config.LLM_PROVIDER == "openai"
        assert Config.LLM_API_KEY == "sk-or-v1-test"
        assert Config.LLM_BASE_URL == "https://openrouter.ai/api/v1"
        assert Config.LLM_MODEL_NAME == "xiaomi/mimo-v2-flash"
        assert Config.SMART_PROVIDER == "openai"
        assert Config.SMART_API_KEY == "sk-or-v1-test"
        assert Config.SMART_MODEL_NAME == "google/gemini-3-flash-preview"
        assert Config.NER_API_KEY == "sk-or-v1-test"
        assert Config.NER_MODEL_NAME == "google/gemini-3-flash-preview"
        assert Config.WONDERWALL_MODEL_NAME == "xiaomi/mimo-v2-flash"
        assert Config.WONDERWALL_BASE_URL == "https://openrouter.ai/api/v1"
        assert Config.WONDERWALL_API_KEY == "sk-or-v1-test"
        assert Config.EMBEDDING_PROVIDER == "openai"
        assert Config.EMBEDDING_MODEL == "openai/text-embedding-3-large"
        assert Config.EMBEDDING_BASE_URL == "https://openrouter.ai/api"
        assert Config.EMBEDDING_API_KEY == "sk-or-v1-test"
        assert Config.EMBEDDING_DIMENSIONS == 768
        assert Config.WEB_SEARCH_MODEL == "google/gemini-3-flash-preview:online"
    finally:
        for attr, value in snapshot.items():
            setattr(Config, attr, value)


def test_sync_process_env_emits_blank_keys_for_removal(monkeypatch):
    emitted = {}
    monkeypatch.setattr(
        settings_api,
        "_set_env_var",
        lambda name, value: emitted.setdefault(name, value),
    )
    monkeypatch.setattr(Config, "LLM_API_KEY", "", raising=False)
    monkeypatch.setattr(Config, "WONDERWALL_API_KEY", "", raising=False)

    settings_api._sync_process_env()

    assert emitted["LLM_API_KEY"] == ""
    assert emitted["WONDERWALL_API_KEY"] == ""
