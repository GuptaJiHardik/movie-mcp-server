from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from letterboxd_mcp.database import Database
from letterboxd_mcp.database.repositories import CacheState, CacheStateRepository


@pytest.fixture
def repository(tmp_path) -> CacheStateRepository:
    database = Database(tmp_path / "server.db")
    database.initialize()
    return CacheStateRepository(database)


def test_get_missing_cache_state_returns_none(repository) -> None:
    assert repository.get("profile", "alice") is None


def test_upsert_round_trips_utc_timestamp(repository) -> None:
    state = CacheState(
        resource_type="profile",
        resource_key="alice",
        fetched_at=datetime(2026, 9, 6, 10, 30, tzinfo=UTC),
    )

    repository.upsert(state)

    assert repository.get("profile", "alice") == state


def test_upsert_replaces_timestamp_for_same_identity(repository) -> None:
    first = CacheState("diary", "alice", datetime(2026, 9, 6, 10, tzinfo=UTC))
    second = CacheState("diary", "alice", first.fetched_at + timedelta(minutes=5))

    repository.upsert(first)
    repository.upsert(second)

    assert repository.get("diary", "alice") == second


def test_timestamp_is_normalized_to_utc(repository) -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    state = CacheState("profile", "alice", datetime(2026, 9, 6, 16, tzinfo=offset))

    repository.upsert(state)
    stored = repository.get("profile", "alice")

    assert stored is not None
    assert stored.fetched_at == datetime(2026, 9, 6, 10, 30, tzinfo=UTC)
    assert stored.fetched_at.tzinfo is UTC


def test_delete_reports_whether_state_existed(repository) -> None:
    repository.upsert(CacheState("profile", "alice", datetime.now(UTC)))

    assert repository.delete("profile", "alice") is True
    assert repository.delete("profile", "alice") is False
    assert repository.get("profile", "alice") is None


def test_cache_state_requires_stable_identity_and_aware_time() -> None:
    with pytest.raises(ValueError, match="resource_type"):
        CacheState("", "alice", datetime.now(UTC))
    with pytest.raises(ValueError, match="resource_key"):
        CacheState("profile", "", datetime.now(UTC))
    with pytest.raises(ValueError, match="timezone-aware"):
        CacheState("profile", "alice", datetime(2026, 9, 6, 10, 30))
