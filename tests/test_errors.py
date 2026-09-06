from __future__ import annotations

import pytest

from letterboxd_mcp.errors import (
    ChallengePageError,
    DatabaseError,
    FilmNotFoundError,
    LetterboxdError,
    LetterboxdFetchError,
    ParseError,
    UserNotFoundError,
)


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (UserNotFoundError("alice"), "Letterboxd user not found: alice"),
        (FilmNotFoundError("arrival"), "Letterboxd film not found: arrival"),
        (
            LetterboxdFetchError(
                "https://letterboxd.com/alice/", status_code=503
            ),
            "Unable to fetch Letterboxd page (HTTP 503): https://letterboxd.com/alice/",
        ),
        (
            ChallengePageError("https://letterboxd.com/alice/", status_code=403),
            "Letterboxd returned a challenge page (HTTP 403): https://letterboxd.com/alice/",
        ),
        (
            ParseError(
                "profile",
                "missing display name",
                url="https://letterboxd.com/alice/",
            ),
            "Unable to parse profile page at https://letterboxd.com/alice/: missing display name",
        ),
        (DatabaseError("upsert profile"), "Database operation failed: upsert profile"),
    ],
)
def test_structured_error_messages(error: LetterboxdError, message: str) -> None:
    assert str(error) == message


def test_structured_errors_keep_machine_readable_context() -> None:
    user_error = UserNotFoundError("alice")
    film_error = FilmNotFoundError("arrival")
    fetch_error = LetterboxdFetchError("https://example.test", status_code=500)
    parse_error = ParseError("diary", "missing table", url="https://example.test")
    database_error = DatabaseError("initialize schema")

    assert user_error.username == "alice"
    assert film_error.film_slug == "arrival"
    assert fetch_error.status_code == 500
    assert fetch_error.url == "https://example.test"
    assert parse_error.page_type == "diary"
    assert parse_error.url == "https://example.test"
    assert database_error.operation == "initialize schema"


def test_all_public_errors_share_one_base_type() -> None:
    errors = [
        UserNotFoundError("alice"),
        FilmNotFoundError("arrival"),
        LetterboxdFetchError("https://example.test"),
        ChallengePageError("https://example.test"),
        ParseError("profile", "broken markup"),
        DatabaseError("query"),
    ]

    assert all(isinstance(error, LetterboxdError) for error in errors)
