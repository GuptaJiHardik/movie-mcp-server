"""Persistence for profile-specific watched-film membership."""

from __future__ import annotations

from datetime import UTC, datetime
import sqlite3

from letterboxd_mcp.database.db import Database
from letterboxd_mcp.database.repositories.films import _film_from_row
from letterboxd_mcp.models import UserFilm


class UserFilmRepository:
    """Store and page a complete ordered watched-film snapshot."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def replace_for_user(self, username: str, films: list[UserFilm]) -> None:
        if any(film.username.casefold() != username.casefold() for film in films):
            raise ValueError("all watched films must belong to the requested user")
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM user_films WHERE username = ?", (username,))
            connection.executemany(
                """
                INSERT INTO user_films (
                    username, film_slug, position, rating, liked, review_url, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.username,
                        item.film.slug,
                        item.position,
                        item.rating,
                        int(item.liked),
                        item.review_url,
                        _serialize_datetime(item.fetched_at),
                    )
                    for item in films
                ],
            )

    def list_for_user(
        self, username: str, *, limit: int, offset: int
    ) -> list[UserFilm]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT uf.username, uf.position, uf.rating, uf.liked,
                       uf.review_url, uf.fetched_at,
                       f.slug AS film_slug, f.title AS film_title,
                       f.year AS film_year, f.url AS film_url,
                       f.poster_url AS film_poster_url,
                       f.fetched_at AS film_fetched_at
                FROM user_films AS uf
                JOIN films AS f ON f.slug = uf.film_slug
                WHERE uf.username = ?
                ORDER BY uf.position
                LIMIT ? OFFSET ?
                """,
                (username, limit, offset),
            ).fetchall()
        return [_from_row(row) for row in rows]

    def count_for_user(self, username: str) -> int:
        with self.database.connection() as connection:
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM user_films WHERE username = ?", (username,)
                ).fetchone()[0]
            )


def _serialize_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _from_row(row: sqlite3.Row) -> UserFilm:
    return UserFilm(
        username=row["username"],
        film=_film_from_row(row, prefix="film_"),
        position=row["position"],
        rating=row["rating"],
        liked=bool(row["liked"]),
        review_url=row["review_url"],
        fetched_at=datetime.fromisoformat(row["fetched_at"].replace("Z", "+00:00")),
    )
