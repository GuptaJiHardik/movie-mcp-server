from __future__ import annotations

from pathlib import Path

import pytest

from letterboxd_mcp.config import Settings


def test_settings_defaults() -> None:
    settings = Settings()

    assert settings.base_url == "https://letterboxd.com"
    assert settings.database_path == Path("server.db")
    assert settings.request_timeout == (5.0, 20.0)
    assert settings.max_retries == 2
    assert settings.profile_ttl_seconds == 1800
    assert settings.diary_ttl_seconds == 600
    assert settings.film_ttl_seconds == 86400


def test_settings_load_from_explicit_environment() -> None:
    settings = Settings.from_env(
        {
            "LETTERBOXD_MCP_BASE_URL": "https://example.test/",
            "LETTERBOXD_MCP_DATABASE_PATH": "data/cache.db",
            "LETTERBOXD_MCP_USER_AGENT": "test-agent",
            "LETTERBOXD_MCP_CONNECT_TIMEOUT_SECONDS": "1.5",
            "LETTERBOXD_MCP_READ_TIMEOUT_SECONDS": "9",
            "LETTERBOXD_MCP_MAX_RETRIES": "4",
            "LETTERBOXD_MCP_RETRY_BACKOFF_SECONDS": "0.25",
            "LETTERBOXD_MCP_PROFILE_TTL_SECONDS": "10",
            "LETTERBOXD_MCP_DIARY_TTL_SECONDS": "20",
            "LETTERBOXD_MCP_FILM_TTL_SECONDS": "30",
            "LETTERBOXD_MCP_COLLECTION_TTL_SECONDS": "40",
            "LETTERBOXD_MCP_POPULAR_TTL_SECONDS": "50",
        }
    )

    assert settings.base_url == "https://example.test"
    assert settings.database_path == Path("data/cache.db")
    assert settings.user_agent == "test-agent"
    assert settings.request_timeout == (1.5, 9.0)
    assert settings.max_retries == 4
    assert settings.retry_backoff_seconds == 0.25
    assert settings.profile_ttl_seconds == 10
    assert settings.diary_ttl_seconds == 20
    assert settings.film_ttl_seconds == 30
    assert settings.collection_ttl_seconds == 40
    assert settings.popular_ttl_seconds == 50


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"LETTERBOXD_MCP_MAX_RETRIES": "many"}, "must be an integer"),
        ({"LETTERBOXD_MCP_READ_TIMEOUT_SECONDS": "slow"}, "must be a number"),
        ({"LETTERBOXD_MCP_PROFILE_TTL_SECONDS": "0"}, "must be greater than zero"),
    ],
)
def test_settings_reject_invalid_environment(
    values: dict[str, str], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        Settings.from_env(values)


def test_settings_reject_invalid_direct_values() -> None:
    with pytest.raises(ValueError, match="base_url"):
        Settings(base_url="letterboxd.test")

    with pytest.raises(ValueError, match="max_retries"):
        Settings(max_retries=-1)

    with pytest.raises(ValueError, match="user_agent"):
        Settings(user_agent="  ")
