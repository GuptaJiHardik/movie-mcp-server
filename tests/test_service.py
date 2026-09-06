from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from letterboxd_mcp.config import Settings
from letterboxd_mcp.errors import LetterboxdFetchError, ParseError, UserNotFoundError
from letterboxd_mcp.service import LetterboxdService


FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 9, 6, 10, 30, tzinfo=UTC)


def make_service(html: str):
    client = Mock()
    client.settings = Settings()
    client.get.return_value = html
    repository = Mock()
    return LetterboxdService(client, repository, clock=lambda: NOW), client, repository


def test_get_profile_fetches_parses_persists_and_returns_profile() -> None:
    service, client, repository = make_service(
        (FIXTURES / "profile_normal.html").read_text(encoding="utf-8")
    )

    profile = service.get_profile(" Alice ")

    assert profile.username == "alice"
    assert profile.fetched_at == NOW
    client.get.assert_called_once_with("/alice/")
    repository.upsert.assert_called_once_with(profile)


def test_get_profile_translates_404_to_user_not_found() -> None:
    service, client, repository = make_service("")
    client.get.side_effect = LetterboxdFetchError(
        "https://letterboxd.com/missing/", status_code=404
    )

    with pytest.raises(UserNotFoundError) as captured:
        service.get_profile("missing")

    assert captured.value.username == "missing"
    repository.upsert.assert_not_called()


def test_get_profile_does_not_persist_malformed_success() -> None:
    service, _, repository = make_service("<html><h1>Oops</h1></html>")

    with pytest.raises(ParseError):
        service.get_profile("alice")

    repository.upsert.assert_not_called()


@pytest.mark.parametrize("username", ["", "../alice", "alice/profile", "alice!"])
def test_get_profile_rejects_unsafe_username_before_fetch(username: str) -> None:
    service, client, repository = make_service("")

    with pytest.raises(ValueError, match="username"):
        service.get_profile(username)

    client.get.assert_not_called()
    repository.upsert.assert_not_called()
