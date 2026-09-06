from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from letterboxd_mcp.database import Database
from letterboxd_mcp.database.repositories import ProfileRepository
from letterboxd_mcp.models import Profile


@pytest.fixture
def repository(tmp_path) -> ProfileRepository:
    database = Database(tmp_path / "server.db")
    database.initialize()
    return ProfileRepository(database)


def make_profile(**changes: object) -> Profile:
    values = {
        "username": "alice",
        "display_name": "Alice Example",
        "bio": "Hello",
        "avatar_url": "https://a.ltrbxd.com/alice.jpg",
        "films_count": 10,
        "followers_count": 20,
        "following_count": 30,
        "fetched_at": datetime(2026, 9, 6, 10, tzinfo=UTC),
    }
    values.update(changes)
    return Profile(**values)


def test_missing_profile_returns_none(repository) -> None:
    assert repository.get("alice") is None


def test_upsert_round_trips_profile(repository) -> None:
    profile = make_profile()

    repository.upsert(profile)

    assert repository.get("ALICE") == profile


def test_upsert_replaces_all_mutable_profile_values(repository) -> None:
    first = make_profile()
    replacement = make_profile(
        display_name="Alice Renamed",
        bio=None,
        avatar_url=None,
        films_count=None,
        followers_count=21,
        following_count=None,
        fetched_at=first.fetched_at + timedelta(minutes=5),
    )

    repository.upsert(first)
    repository.upsert(replacement)

    assert repository.get("alice") == replacement
