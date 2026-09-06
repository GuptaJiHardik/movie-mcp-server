"""Persistence for normalized public profiles."""

from __future__ import annotations

from datetime import UTC, datetime
import sqlite3

from letterboxd_mcp.database.db import Database
from letterboxd_mcp.models import Profile


class ProfileRepository:
    """Read and UPSERT profiles by their case-insensitive username."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def get(self, username: str) -> Profile | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT username, display_name, bio, avatar_url, films_count,
                       followers_count, following_count, fetched_at
                FROM profiles
                WHERE username = ?
                """,
                (username,),
            ).fetchone()

        return None if row is None else _from_row(row)

    def upsert(self, profile: Profile) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO profiles (
                    username, display_name, bio, avatar_url, films_count,
                    followers_count, following_count, fetched_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    display_name = excluded.display_name,
                    bio = excluded.bio,
                    avatar_url = excluded.avatar_url,
                    films_count = excluded.films_count,
                    followers_count = excluded.followers_count,
                    following_count = excluded.following_count,
                    fetched_at = excluded.fetched_at
                """,
                (
                    profile.username,
                    profile.display_name,
                    profile.bio,
                    profile.avatar_url,
                    profile.films_count,
                    profile.followers_count,
                    profile.following_count,
                    _serialize_datetime(profile.fetched_at),
                ),
            )


def _serialize_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _from_row(row: sqlite3.Row) -> Profile:
    return Profile(
        username=row["username"],
        display_name=row["display_name"],
        bio=row["bio"],
        avatar_url=row["avatar_url"],
        films_count=row["films_count"],
        followers_count=row["followers_count"],
        following_count=row["following_count"],
        fetched_at=datetime.fromisoformat(row["fetched_at"].replace("Z", "+00:00")),
    )
