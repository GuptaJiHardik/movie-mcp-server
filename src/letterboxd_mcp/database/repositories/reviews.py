"""Persistence for profile-authored public reviews."""

from __future__ import annotations

from datetime import UTC, date, datetime

from letterboxd_mcp.database.db import Database
from letterboxd_mcp.models import UserReview


class ReviewRepository:
    """Read and UPSERT normalized reviews by stable viewing identity."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def get_by_url(self, review_url: str) -> UserReview | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT id, username, film_slug, review_url, reviewed_date,
                       rating, liked, contains_spoilers, review_text, fetched_at
                FROM reviews WHERE review_url = ?
                """,
                (review_url,),
            ).fetchone()
        if row is None or row["review_text"] is None:
            return None
        return UserReview(
            id=row["id"],
            username=row["username"],
            film_slug=row["film_slug"],
            review_url=row["review_url"],
            reviewed_date=(
                date.fromisoformat(row["reviewed_date"])
                if row["reviewed_date"]
                else None
            ),
            rating=row["rating"],
            liked=bool(row["liked"]),
            contains_spoilers=bool(row["contains_spoilers"]),
            review_text=row["review_text"],
            fetched_at=datetime.fromisoformat(row["fetched_at"].replace("Z", "+00:00")),
        )

    def upsert(self, review: UserReview) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO reviews (
                    id, username, film_slug, review_url, reviewed_date,
                    rating, liked, contains_spoilers, review_text, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(review_url) DO UPDATE SET
                    username = excluded.username,
                    film_slug = excluded.film_slug,
                    review_url = excluded.review_url,
                    reviewed_date = excluded.reviewed_date,
                    rating = excluded.rating,
                    liked = excluded.liked,
                    contains_spoilers = excluded.contains_spoilers,
                    review_text = excluded.review_text,
                    fetched_at = excluded.fetched_at
                """,
                (
                    review.id,
                    review.username,
                    review.film_slug,
                    review.review_url,
                    review.reviewed_date.isoformat() if review.reviewed_date else None,
                    review.rating,
                    int(review.liked),
                    int(review.contains_spoilers),
                    review.review_text,
                    _serialize_datetime(review.fetched_at),
                ),
            )


def _serialize_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
