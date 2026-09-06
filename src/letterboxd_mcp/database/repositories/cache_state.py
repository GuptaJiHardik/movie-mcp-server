"""Persistence for resource fetch timestamps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import sqlite3

from letterboxd_mcp.database.db import Database


@dataclass(frozen=True, slots=True)
class CacheState:
    """The most recent successful fetch for one logical resource."""

    resource_type: str
    resource_key: str
    fetched_at: datetime

    def __post_init__(self) -> None:
        if not self.resource_type.strip():
            raise ValueError("resource_type must not be empty")
        if not self.resource_key.strip():
            raise ValueError("resource_key must not be empty")
        if self.fetched_at.tzinfo is None:
            raise ValueError("fetched_at must be timezone-aware")


class CacheStateRepository:
    """Read and UPSERT cache state by stable resource identity."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def get(self, resource_type: str, resource_key: str) -> CacheState | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT resource_type, resource_key, fetched_at
                FROM cache_state
                WHERE resource_type = ? AND resource_key = ?
                """,
                (resource_type, resource_key),
            ).fetchone()

        if row is None:
            return None
        return _from_row(row)

    def upsert(self, state: CacheState) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO cache_state (resource_type, resource_key, fetched_at)
                VALUES (?, ?, ?)
                ON CONFLICT(resource_type, resource_key) DO UPDATE SET
                    fetched_at = excluded.fetched_at
                """,
                (
                    state.resource_type,
                    state.resource_key,
                    _serialize_datetime(state.fetched_at),
                ),
            )

    def delete(self, resource_type: str, resource_key: str) -> bool:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                DELETE FROM cache_state
                WHERE resource_type = ? AND resource_key = ?
                """,
                (resource_type, resource_key),
            )
            return cursor.rowcount > 0


def _serialize_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _from_row(row: sqlite3.Row) -> CacheState:
    return CacheState(
        resource_type=row["resource_type"],
        resource_key=row["resource_key"],
        fetched_at=datetime.fromisoformat(row["fetched_at"].replace("Z", "+00:00")),
    )
