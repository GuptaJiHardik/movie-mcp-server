from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from letterboxd_mcp.errors import ParseError
from letterboxd_mcp.parsers import parse_profile


FIXTURES = Path(__file__).parent / "fixtures"
FETCHED_AT = datetime(2026, 9, 6, 10, 30, tzinfo=UTC)


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parses_normal_profile_fixture() -> None:
    profile = parse_profile(
        fixture("profile_normal.html"),
        username="alice",
        fetched_at=FETCHED_AT,
        url="https://letterboxd.com/alice/",
    )

    assert profile.username == "alice"
    assert profile.display_name == "Alice Example"
    assert profile.bio == "Films, tea & rainy days.\nThey/them."
    assert profile.avatar_url == "https://a.ltrbxd.com/alice.jpg"
    assert profile.films_count == 1234
    assert profile.following_count == 56
    assert profile.followers_count == 7890
    assert profile.fetched_at == FETCHED_AT


def test_sparse_profile_preserves_missing_optional_values() -> None:
    profile = parse_profile(
        fixture("profile_sparse.html"), username="bob", fetched_at=FETCHED_AT
    )

    assert profile.display_name == "bob"
    assert profile.bio is None
    assert profile.avatar_url is None
    assert profile.films_count is None
    assert profile.following_count is None
    assert profile.followers_count is None


def test_unrecognized_optional_count_is_preserved_as_missing() -> None:
    html = fixture("profile_sparse.html").replace(
        "</section>",
        '<div class="profile-stats"><h4 class="profile-statistic">'
        '<span class="value">many</span><span class="definition">Films</span>'
        "</h4></div></section>",
    )

    profile = parse_profile(html, username="bob", fetched_at=FETCHED_AT)

    assert profile.films_count is None


@pytest.mark.parametrize(
    "html,message",
    [
        ("<html><h1>Temporary problem</h1></html>", "missing profile header"),
        (
            '<section class="profile-header" data-person="alice"></section>',
            "missing display name",
        ),
    ],
)
def test_unexpected_success_markup_raises_parse_error(html: str, message: str) -> None:
    with pytest.raises(ParseError, match=message):
        parse_profile(
            html,
            username="alice",
            fetched_at=FETCHED_AT,
            url="https://letterboxd.com/alice/",
        )
