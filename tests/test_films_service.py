from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from fastmcp import Client

from letterboxd_mcp.config import Settings
from letterboxd_mcp.database import Database
from letterboxd_mcp.database.repositories import (
    CacheStateRepository,
    DiaryEntryRepository,
    FilmDetailsRepository,
    FilmRepository,
    ProfileRepository,
    ReviewRepository,
    UserFilmRepository,
)
from letterboxd_mcp.server import create_mcp
from letterboxd_mcp.service import LetterboxdService


FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 9, 6, 12, tzinfo=UTC)


def diary_html() -> str:
    return """
    <table id="diary-table" class="diary-table">
      <tr class="diary-entry-row" data-viewing-id="2">
        <td class="col-daydate"><a class="daydate" href="/alice/diary/for/2026/09/06/">6</a></td>
        <td class="col-production"><div data-item-slug="alpha"></div><h2 class="primaryname"><a>Alpha</a></h2></td>
        <td class="col-releaseyear">2024</td><td class="col-rating"><span class="rating rated-9"></span></td>
        <td class="col-rewatch icon-status-on"></td><td class="col-like"><span class="icon-liked"></span></td>
        <td class="col-review"><a href="/alice/film/alpha/">Review</a></td>
      </tr>
      <tr class="diary-entry-row" data-viewing-id="1">
        <td class="col-daydate"><a class="daydate" href="/alice/diary/for/2025/01/02/">2</a></td>
        <td class="col-production"><div data-item-slug="alpha"></div><h2 class="primaryname"><a>Alpha</a></h2></td>
        <td class="col-releaseyear">2024</td><td class="col-rating"><span class="rating rated-8"></span></td>
        <td class="col-rewatch icon-status-off"></td><td class="col-like"></td>
      </tr>
    </table>
    """


class FakeClient:
    def __init__(self, database_path: Path) -> None:
        self.settings = Settings(database_path=database_path)
        self.calls: list[str] = []
        self.watched = (FIXTURES / "watched_page.html").read_text(encoding="utf-8")
        self.details = (FIXTURES / "film_details.html").read_text(encoding="utf-8")
        self.review = (FIXTURES / "review.html").read_text(encoding="utf-8")

    def get(self, path: str) -> str:
        self.calls.append(path)
        if path == "/alice/films/by/added/":
            return self.watched
        if path == "/alice/films/by/added/page/2/":
            return '<div class="poster-grid"><ul class="grid"></ul></div>'
        if path == "/alice/diary/":
            return diary_html()
        if path in {"/film/alpha/", "/film/beta/"}:
            return self.details
        if path == "/alice/film/alpha/":
            return self.review
        raise AssertionError(f"unexpected HTTP path: {path}")


def make_service(tmp_path):
    database = Database(tmp_path / "server.db")
    database.initialize()
    client = FakeClient(database.path)
    service = LetterboxdService(
        client,
        ProfileRepository(database),
        film_repository=FilmRepository(database),
        diary_repository=DiaryEntryRepository(database),
        cache_repository=CacheStateRepository(database),
        user_film_repository=UserFilmRepository(database),
        film_details_repository=FilmDetailsRepository(database),
        review_repository=ReviewRepository(database),
        clock=lambda: NOW,
    )
    return service, client


def test_get_films_syncs_enriches_pages_and_reuses_cache(tmp_path) -> None:
    service, client = make_service(tmp_path)

    first = service.get_films(" Alice ", limit=1)

    assert first.username == "alice"
    assert first.total == 2
    assert first.has_more is True
    assert first.items[0].film.slug == "alpha"
    assert first.items[0].film.average_rating == 4.21
    assert first.items[0].user_rating == 4.5
    assert len(first.items[0].viewings) == 2
    assert first.items[0].viewings[0].rewatch is True
    assert first.items[0].latest_review.review_text.startswith("First paragraph")
    assert client.calls == [
        "/alice/films/by/added/",
        "/alice/films/by/added/page/2/",
        "/alice/diary/",
        "/film/alpha/",
        "/alice/film/alpha/",
    ]

    calls_after_first = len(client.calls)
    assert service.get_films("alice", limit=1) == first
    assert len(client.calls) == calls_after_first

    second = service.get_films("alice", limit=1, offset=1)
    assert second.items[0].film.slug == "beta"
    assert second.has_more is False
    assert client.calls[-1] == "/film/beta/"

    service.get_films("alice", limit=1, refresh=True)
    assert client.calls.count("/alice/films/by/added/") == 2
    assert client.calls.count("/alice/diary/") == 2
    assert client.calls.count("/film/alpha/") == 2
    assert client.calls.count("/alice/film/alpha/") == 2


def test_get_films_validates_bounds_before_http(tmp_path) -> None:
    service, client = make_service(tmp_path)

    for kwargs in ({"limit": 0}, {"limit": 21}, {"offset": -1}):
        try:
            service.get_films("alice", **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid paging arguments were accepted")

    assert client.calls == []


def test_get_films_serializes_through_mcp(tmp_path) -> None:
    service, _ = make_service(tmp_path)

    async def call_tool():
        async with Client(create_mcp(service)) as client:
            return await client.call_tool(
                "get_films", {"username": "alice", "limit": 1}
            )

    result = asyncio.run(call_tool())

    assert result.structured_content["username"] == "alice"
    assert result.structured_content["items"][0]["film"]["directors"] == [
        "Director One"
    ]
