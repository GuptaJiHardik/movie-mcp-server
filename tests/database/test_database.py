from __future__ import annotations

import sqlite3

import pytest

from letterboxd_mcp.database import Database
from letterboxd_mcp.errors import DatabaseError


EXPECTED_TABLES = {
    "profiles",
    "films",
    "diary_entries",
    "reviews",
    "watchlist",
    "lists",
    "list_items",
    "cache_state",
}

EXPECTED_INDEXES = {
    "idx_diary_entries_username_watched_date",
    "idx_diary_entries_username_film_slug",
    "idx_reviews_username",
    "idx_watchlist_username",
    "idx_films_title",
}


def test_initialize_creates_all_tables_and_indexes(tmp_path) -> None:
    database = Database(tmp_path / "server.db")

    database.initialize()

    with database.connection() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        indexes = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            )
        }
        foreign_keys_enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]

    assert EXPECTED_TABLES <= tables
    assert EXPECTED_INDEXES <= indexes
    assert foreign_keys_enabled == 1


def test_initialize_is_idempotent(tmp_path) -> None:
    database = Database(tmp_path / "server.db")

    database.initialize()
    database.initialize()

    with database.connection() as connection:
        table_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table' AND name IN ({})
            """.format(",".join("?" for _ in EXPECTED_TABLES)),
            tuple(EXPECTED_TABLES),
        ).fetchone()[0]

    assert table_count == len(EXPECTED_TABLES)


def test_transaction_commits_successful_work(tmp_path) -> None:
    database = Database(tmp_path / "server.db")
    database.initialize()

    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO cache_state (resource_type, resource_key, fetched_at)
            VALUES ('profile', 'alice', '2026-09-06T10:00:00Z')
            """
        )

    with database.connection() as connection:
        count = connection.execute("SELECT COUNT(*) FROM cache_state").fetchone()[0]

    assert count == 1


def test_transaction_rolls_back_caller_failure(tmp_path) -> None:
    database = Database(tmp_path / "server.db")
    database.initialize()

    with pytest.raises(RuntimeError, match="stop"):
        with database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO cache_state (resource_type, resource_key, fetched_at)
                VALUES ('profile', 'alice', '2026-09-06T10:00:00Z')
                """
            )
            raise RuntimeError("stop")

    with database.connection() as connection:
        count = connection.execute("SELECT COUNT(*) FROM cache_state").fetchone()[0]

    assert count == 0


def test_sqlite_failure_is_wrapped_with_original_cause(tmp_path) -> None:
    database = Database(tmp_path / "missing" / "server.db")

    with pytest.raises(DatabaseError) as captured:
        database.initialize()

    assert isinstance(captured.value.__cause__, sqlite3.Error)
