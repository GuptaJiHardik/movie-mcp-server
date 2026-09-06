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
    "user_films",
    "film_details",
    "film_directors",
    "film_cast",
    "film_genres",
}

EXPECTED_INDEXES = {
    "idx_diary_entries_username_watched_date",
    "idx_diary_entries_username_film_slug",
    "idx_reviews_username",
    "idx_watchlist_username",
    "idx_films_title",
    "idx_reviews_review_url",
    "idx_user_films_username_position",
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


def test_initialize_migrates_existing_reviews_table(tmp_path) -> None:
    path = tmp_path / "server.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE reviews (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                film_slug TEXT NOT NULL,
                review_url TEXT NOT NULL,
                reviewed_date TEXT,
                rating REAL,
                liked INTEGER,
                review_text TEXT,
                fetched_at TEXT NOT NULL
            )
            """
        )

    database = Database(path)
    database.initialize()

    with database.connection() as connection:
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(reviews)")
        }

    assert "contains_spoilers" in columns


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
