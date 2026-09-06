from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from letterboxd_mcp.database import Database
from letterboxd_mcp.database.repositories import (
    FilmDetailsRepository,
    FilmRepository,
    ReviewRepository,
    UserFilmRepository,
)
from letterboxd_mcp.errors import ParseError
from letterboxd_mcp.parsers import (
    parse_diary_page,
    parse_film_details,
    parse_review,
    parse_watched_page,
)


FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 9, 6, 12, tzinfo=UTC)


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_watched_parser_normalizes_membership_and_pagination() -> None:
    parsed = parse_watched_page(
        fixture("watched_page.html"),
        username="alice",
        fetched_at=NOW,
        start_position=7,
    )

    assert parsed.next_path == "/alice/films/by/added/page/2/"
    assert [item.film.slug for item in parsed.films] == ["alpha", "beta"]
    assert [item.position for item in parsed.films] == [7, 8]
    assert parsed.films[0].rating == 4.5
    assert parsed.films[0].liked is True
    assert parsed.films[0].review_url == "/alice/film/alpha/"
    assert parsed.films[1].film.year is None
    assert parsed.films[1].film.poster_url is None


def test_film_details_parser_reads_core_metadata_and_top_cast() -> None:
    details = parse_film_details(
        fixture("film_details.html"), slug="alpha", fetched_at=NOW
    )

    assert details.title == "Alpha"
    assert details.original_title == "Αλφα"
    assert details.runtime_minutes == 125
    assert details.directors == ("Director One",)
    assert details.genres == ("Drama", "Thriller")
    assert details.average_rating == 4.21
    assert details.cast[0].model_dump() == {
        "name": "Actor One",
        "role": "Lead",
        "url": "/actor/actor-one/",
    }


def test_review_parser_reads_profile_review_metadata() -> None:
    review = parse_review(
        fixture("review.html"),
        username="alice",
        film_slug="alpha",
        review_url="/alice/film/alpha/",
        fetched_at=NOW,
    )

    assert review.id == "12345"
    assert review.reviewed_date.isoformat() == "2026-09-06"
    assert review.rating == 4.5
    assert review.liked is True
    assert review.contains_spoilers is True
    assert review.review_text == "First paragraph.\nSecond paragraph."


@pytest.mark.parametrize(
    ("parser", "kwargs"),
    [
        (parse_watched_page, {"username": "alice", "fetched_at": NOW}),
        (parse_film_details, {"slug": "alpha", "fetched_at": NOW}),
        (
            parse_review,
            {
                "username": "alice",
                "film_slug": "alpha",
                "review_url": "/alice/film/alpha/",
                "fetched_at": NOW,
            },
        ),
    ],
)
def test_new_parsers_reject_missing_page_boundaries(parser, kwargs) -> None:
    with pytest.raises(ParseError):
        parser("<html></html>", **kwargs)


def test_empty_public_diary_boundary_returns_no_entries() -> None:
    parsed = parse_diary_page(
        '<section class="profile-header" data-person="alice"></section>',
        username="alice",
        fetched_at=NOW,
    )

    assert parsed.entries == ()
    assert parsed.next_path is None


def test_new_repositories_round_trip_and_replace_snapshots(tmp_path) -> None:
    database = Database(tmp_path / "server.db")
    database.initialize()
    films = FilmRepository(database)
    user_films = UserFilmRepository(database)
    details_repository = FilmDetailsRepository(database)
    reviews = ReviewRepository(database)

    parsed = parse_watched_page(
        fixture("watched_page.html"), username="alice", fetched_at=NOW
    )
    details = parse_film_details(
        fixture("film_details.html"), slug="alpha", fetched_at=NOW
    )
    review = parse_review(
        fixture("review.html"),
        username="alice",
        film_slug="alpha",
        review_url="/alice/film/alpha/",
        fetched_at=NOW,
    )
    films.upsert_many([item.film for item in parsed.films])
    user_films.replace_for_user("alice", list(parsed.films))
    films.upsert_many([details])
    details_repository.replace(details)
    reviews.upsert(review)

    assert user_films.count_for_user("alice") == 2
    assert user_films.list_for_user("alice", limit=1, offset=1)[0].film.slug == "beta"
    assert details_repository.get("alpha") == details
    assert reviews.get_by_url(review.review_url) == review

    user_films.replace_for_user("alice", [parsed.films[1].model_copy(update={"position": 0})])
    assert user_films.count_for_user("alice") == 1
