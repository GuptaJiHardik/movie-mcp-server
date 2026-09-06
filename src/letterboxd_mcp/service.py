"""Application services coordinating public Letterboxd reads."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
import re
from urllib.parse import urljoin

from letterboxd_mcp.client import LetterboxdClient
from letterboxd_mcp.database.repositories import (
    CacheState,
    CacheStateRepository,
    DiaryEntryRepository,
    FilmRepository,
    ProfileRepository,
)
from letterboxd_mcp.errors import LetterboxdFetchError, ParseError, UserNotFoundError
from letterboxd_mcp.models import DiaryEntry, Profile
from letterboxd_mcp.parsers import parse_diary_page, parse_profile


_USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_-]*\Z")


class LetterboxdService:
    """Coordinate HTTP, parsing, and persistence without UI concerns."""

    def __init__(
        self,
        client: LetterboxdClient,
        profile_repository: ProfileRepository,
        *,
        film_repository: FilmRepository | None = None,
        diary_repository: DiaryEntryRepository | None = None,
        cache_repository: CacheStateRepository | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.client = client
        self.profile_repository = profile_repository
        self.film_repository = film_repository
        self.diary_repository = diary_repository
        self.cache_repository = cache_repository
        self._clock = clock

    def get_profile(self, username: str, refresh: bool = False) -> Profile:
        """Return a fresh cached profile or fetch and persist a new copy."""
        normalized_username = _normalize_username(username)
        checked_at = self._clock()
        if not refresh and self.cache_repository is not None:
            state = self.cache_repository.get("profile", normalized_username)
            cached = self.profile_repository.get(normalized_username)
            if cached is not None and _is_fresh(
                state,
                now=checked_at,
                ttl_seconds=self.client.settings.profile_ttl_seconds,
            ):
                return cached

        path = f"/{normalized_username}/"
        url = f"{self.client.settings.base_url}{path}"

        try:
            html = self.client.get(path)
        except LetterboxdFetchError as error:
            if error.status_code == 404:
                raise UserNotFoundError(normalized_username) from error
            raise

        profile = parse_profile(
            html,
            username=normalized_username,
            fetched_at=checked_at,
            url=url,
        )
        self.profile_repository.upsert(profile)
        if self.cache_repository is not None:
            self.cache_repository.upsert(
                CacheState("profile", normalized_username, checked_at)
            )
        return profile

    def get_diary(
        self,
        username: str,
        limit: int = 50,
        refresh: bool = False,
    ) -> list[DiaryEntry]:
        """Return cached diary entries or refresh enough public diary pages."""
        if limit <= 0:
            raise ValueError("limit must be positive")
        if self.film_repository is None or self.diary_repository is None:
            raise RuntimeError("diary repositories are not configured")

        normalized_username = _normalize_username(username)
        checked_at = self._clock()
        if not refresh and self.cache_repository is not None:
            cached = self.diary_repository.list_for_user(
                normalized_username,
                limit=limit,
            )
            state = self.cache_repository.get("diary", normalized_username)
            complete_state = self.cache_repository.get(
                "diary_complete",
                normalized_username,
            )
            ttl = self.client.settings.diary_ttl_seconds
            if _is_fresh(state, now=checked_at, ttl_seconds=ttl) and (
                len(cached) >= limit
                or (
                    _is_fresh(complete_state, now=checked_at, ttl_seconds=ttl)
                    and complete_state is not None
                    and state is not None
                    and complete_state.fetched_at == state.fetched_at
                )
            ):
                return cached

        path: str | None = f"/{normalized_username}/diary/"
        seen_paths: set[str] = set()
        entries: list[DiaryEntry] = []
        is_complete = False

        while path is not None and len(entries) < limit:
            if path in seen_paths:
                raise ParseError("diary", "pagination loop detected", url=path)
            seen_paths.add(path)
            page_url = urljoin(f"{self.client.settings.base_url}/", path)

            try:
                html = self.client.get(path)
            except LetterboxdFetchError as error:
                if error.status_code == 404:
                    raise UserNotFoundError(normalized_username) from error
                raise

            parsed = parse_diary_page(
                html,
                username=normalized_username,
                fetched_at=checked_at,
                url=page_url,
            )
            remaining = limit - len(entries)
            selected = list(parsed.entries[:remaining])
            entries.extend(selected)
            path = parsed.next_path
            is_complete = path is None and len(parsed.entries) <= remaining

        self.film_repository.upsert_many([entry.film for entry in entries])
        self.diary_repository.replace_for_user(normalized_username, entries)
        if self.cache_repository is not None:
            self.cache_repository.upsert(
                CacheState("diary", normalized_username, checked_at)
            )
            if is_complete:
                self.cache_repository.upsert(
                    CacheState("diary_complete", normalized_username, checked_at)
                )
            else:
                self.cache_repository.delete("diary_complete", normalized_username)
        return entries


def _normalize_username(username: str) -> str:
    normalized = username.strip()
    if not _USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("username must contain only letters, numbers, underscores, or hyphens")
    return normalized.casefold()


def _is_fresh(
    state: CacheState | None,
    *,
    now: datetime,
    ttl_seconds: int,
) -> bool:
    if state is None:
        return False
    return now - state.fetched_at <= timedelta(seconds=ttl_seconds)
