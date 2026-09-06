"""SQLite connection, schema initialization, and transaction management."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
import sqlite3

from letterboxd_mcp.errors import DatabaseError


class Database:
    """Own SQLite connections for one local database file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a configured connection and always close it."""
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(self.path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            yield connection
        except sqlite3.Error as error:
            raise DatabaseError("open or use SQLite connection", str(error)) from error
        finally:
            if connection is not None:
                connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Commit successful work and roll back any failed transaction."""
        with self.connection() as connection:
            try:
                connection.execute("BEGIN")
                yield connection
                connection.commit()
            except sqlite3.Error as error:
                connection.rollback()
                raise DatabaseError("execute SQLite transaction", str(error)) from error
            except BaseException:
                connection.rollback()
                raise

    def initialize(self) -> None:
        """Create the schema and indexes if they do not already exist."""
        try:
            schema = (
                resources.files("letterboxd_mcp.database")
                .joinpath("schema.sql")
                .read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError) as error:
            raise DatabaseError("load SQLite schema", str(error)) from error

        with self.connection() as connection:
            try:
                connection.executescript(schema)
                review_columns = {
                    row["name"]
                    for row in connection.execute("PRAGMA table_info(reviews)")
                }
                if "contains_spoilers" not in review_columns:
                    connection.execute(
                        """
                        ALTER TABLE reviews
                        ADD COLUMN contains_spoilers INTEGER NOT NULL DEFAULT 0
                        CHECK (contains_spoilers IN (0, 1))
                        """
                    )
                connection.commit()
            except sqlite3.Error as error:
                connection.rollback()
                raise DatabaseError("initialize SQLite schema", str(error)) from error
