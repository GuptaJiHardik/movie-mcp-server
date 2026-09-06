"""Persistence for normalized film summaries."""

from __future__ import annotations

from datetime import UTC, datetime
import sqlite3

from letterboxd_mcp.database.db import Database
from letterboxd_mcp.models import Film


class FilmRepository:
    """Read and UPSERT films by canonical Letterboxd slug."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def get(self, slug: str) -> Film | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT slug, title, year, url, poster_url, fetched_at
                FROM films
                WHERE slug = ?
                """,
                (slug,),
            ).fetchone()
        return None if row is None else _film_from_row(row)

    def upsert_many(self, films: list[Film]) -> None:
        if not films:
            return
        with self.database.transaction() as connection:
            connection.executemany(
                """
                INSERT INTO films (slug, title, year, url, poster_url, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    title = excluded.title,
                    year = COALESCE(excluded.year, films.year),
                    url = excluded.url,
                    poster_url = COALESCE(excluded.poster_url, films.poster_url),
                    fetched_at = excluded.fetched_at
                """,
                [
                    (
                        film.slug,
                        film.title,
                        film.year,
                        film.url,
                        film.poster_url,
                        _serialize_datetime(film.fetched_at),
                    )
                    for film in films
                ],
            )


def _serialize_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _film_from_row(row: sqlite3.Row, *, prefix: str = "") -> Film:
    return Film(
        slug=row[f"{prefix}slug"],
        title=row[f"{prefix}title"],
        year=row[f"{prefix}year"],
        url=row[f"{prefix}url"],
        poster_url=row[f"{prefix}poster_url"],
        fetched_at=datetime.fromisoformat(
            row[f"{prefix}fetched_at"].replace("Z", "+00:00")
        ),
    )
