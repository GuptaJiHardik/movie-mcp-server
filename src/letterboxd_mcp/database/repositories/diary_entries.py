"""Persistence for normalized public diary entries."""

from __future__ import annotations

from datetime import UTC, date, datetime
import sqlite3

from letterboxd_mcp.database.db import Database
from letterboxd_mcp.database.repositories.films import _film_from_row
from letterboxd_mcp.models import DiaryEntry


class DiaryEntryRepository:
    """Read and UPSERT diary entries by stable viewing identity."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def list_for_user(self, username: str, *, limit: int = 50) -> list[DiaryEntry]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT d.id, d.username, d.watched_date, d.rating, d.rewatch,
                       d.liked, d.review_url, d.fetched_at,
                       f.slug AS film_slug, f.title AS film_title,
                       f.year AS film_year, f.url AS film_url,
                       f.poster_url AS film_poster_url,
                       f.fetched_at AS film_fetched_at
                FROM diary_entries AS d
                JOIN films AS f ON f.slug = d.film_slug
                WHERE d.username = ?
                ORDER BY d.watched_date DESC, d.id DESC
                LIMIT ?
                """,
                (username, limit),
            ).fetchall()
        return [_entry_from_row(row) for row in rows]

    def upsert_many(self, entries: list[DiaryEntry]) -> None:
        if not entries:
            return
        with self.database.transaction() as connection:
            connection.executemany(
                """
                INSERT INTO diary_entries (
                    id, username, film_slug, watched_date, rating, rewatch,
                    liked, review_url, fetched_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    username = excluded.username,
                    film_slug = excluded.film_slug,
                    watched_date = excluded.watched_date,
                    rating = excluded.rating,
                    rewatch = excluded.rewatch,
                    liked = excluded.liked,
                    review_url = excluded.review_url,
                    fetched_at = excluded.fetched_at
                """,
                [
                    (
                        entry.id,
                        entry.username,
                        entry.film.slug,
                        entry.watched_date.isoformat(),
                        entry.rating,
                        int(entry.rewatch),
                        None if entry.liked is None else int(entry.liked),
                        entry.review_url,
                        _serialize_datetime(entry.fetched_at),
                    )
                    for entry in entries
                ],
            )


def _serialize_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _entry_from_row(row: sqlite3.Row) -> DiaryEntry:
    return DiaryEntry(
        id=row["id"],
        username=row["username"],
        film=_film_from_row(row, prefix="film_"),
        watched_date=date.fromisoformat(row["watched_date"]),
        rating=row["rating"],
        rewatch=bool(row["rewatch"]),
        liked=None if row["liked"] is None else bool(row["liked"]),
        review_url=row["review_url"],
        fetched_at=datetime.fromisoformat(row["fetched_at"].replace("Z", "+00:00")),
    )
