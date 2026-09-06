"""Persistence for generic enriched film metadata."""

from __future__ import annotations

from datetime import UTC, datetime

from letterboxd_mcp.database.db import Database
from letterboxd_mcp.models import CastMember, FilmDetails


class FilmDetailsRepository:
    """Read and atomically replace one film's enriched metadata."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def get(self, slug: str) -> FilmDetails | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT f.slug, f.title, f.year, f.url, f.poster_url,
                       d.original_title, d.tagline, d.synopsis,
                       d.runtime_minutes, d.average_rating, d.fetched_at
                FROM film_details AS d
                JOIN films AS f ON f.slug = d.film_slug
                WHERE d.film_slug = ?
                """,
                (slug,),
            ).fetchone()
            if row is None:
                return None
            directors = tuple(
                item["name"]
                for item in connection.execute(
                    "SELECT name FROM film_directors WHERE film_slug = ? ORDER BY position",
                    (slug,),
                )
            )
            genres = tuple(
                item["name"]
                for item in connection.execute(
                    "SELECT name FROM film_genres WHERE film_slug = ? ORDER BY position",
                    (slug,),
                )
            )
            cast = tuple(
                CastMember(name=item["name"], role=item["role"], url=item["url"])
                for item in connection.execute(
                    "SELECT name, role, url FROM film_cast WHERE film_slug = ? ORDER BY position",
                    (slug,),
                )
            )
        return FilmDetails(
            slug=row["slug"],
            title=row["title"],
            year=row["year"],
            url=row["url"],
            poster_url=row["poster_url"],
            fetched_at=datetime.fromisoformat(row["fetched_at"].replace("Z", "+00:00")),
            original_title=row["original_title"],
            tagline=row["tagline"],
            synopsis=row["synopsis"],
            runtime_minutes=row["runtime_minutes"],
            directors=directors,
            genres=genres,
            cast=cast,
            average_rating=row["average_rating"],
        )

    def replace(self, details: FilmDetails) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO film_details (
                    film_slug, original_title, tagline, synopsis,
                    runtime_minutes, average_rating, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(film_slug) DO UPDATE SET
                    original_title = excluded.original_title,
                    tagline = excluded.tagline,
                    synopsis = excluded.synopsis,
                    runtime_minutes = excluded.runtime_minutes,
                    average_rating = excluded.average_rating,
                    fetched_at = excluded.fetched_at
                """,
                (
                    details.slug,
                    details.original_title,
                    details.tagline,
                    details.synopsis,
                    details.runtime_minutes,
                    details.average_rating,
                    _serialize_datetime(details.fetched_at),
                ),
            )
            for table in ("film_directors", "film_genres", "film_cast"):
                connection.execute(f"DELETE FROM {table} WHERE film_slug = ?", (details.slug,))
            connection.executemany(
                "INSERT INTO film_directors (film_slug, position, name) VALUES (?, ?, ?)",
                [(details.slug, index, name) for index, name in enumerate(details.directors)],
            )
            connection.executemany(
                "INSERT INTO film_genres (film_slug, position, name) VALUES (?, ?, ?)",
                [(details.slug, index, name) for index, name in enumerate(details.genres)],
            )
            connection.executemany(
                """
                INSERT INTO film_cast (film_slug, position, name, role, url)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (details.slug, index, member.name, member.role, member.url)
                    for index, member in enumerate(details.cast)
                ],
            )


def _serialize_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
