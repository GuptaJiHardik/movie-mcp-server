"""Application services coordinating public Letterboxd reads."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import re
from urllib.parse import urljoin

from letterboxd_mcp.client import LetterboxdClient
from letterboxd_mcp.database.repositories import (
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
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.client = client
        self.profile_repository = profile_repository
        self.film_repository = film_repository
        self.diary_repository = diary_repository
        self._clock = clock

    def get_profile(self, username: str, refresh: bool = False) -> Profile:
        """Fetch, parse, persist, and return a public profile.

        Cache freshness is introduced in the dedicated cache feature. Until then,
        profile reads always fetch, so ``refresh`` is accepted for API stability.
        """
        del refresh
        normalized_username = _normalize_username(username)
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
            fetched_at=self._clock(),
            url=url,
        )
        self.profile_repository.upsert(profile)
        return profile

    def get_diary(
        self,
        username: str,
        limit: int = 50,
        refresh: bool = False,
    ) -> list[DiaryEntry]:
        """Fetch public diary pages until the requested number is persisted."""
        del refresh
        if limit <= 0:
            raise ValueError("limit must be positive")
        if self.film_repository is None or self.diary_repository is None:
            raise RuntimeError("diary repositories are not configured")

        normalized_username = _normalize_username(username)
        path: str | None = f"/{normalized_username}/diary/"
        seen_paths: set[str] = set()
        entries: list[DiaryEntry] = []

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
                fetched_at=self._clock(),
                url=page_url,
            )
            remaining = limit - len(entries)
            selected = list(parsed.entries[:remaining])
            self.film_repository.upsert_many([entry.film for entry in selected])
            self.diary_repository.upsert_many(selected)
            entries.extend(selected)
            path = parsed.next_path

        return entries


def _normalize_username(username: str) -> str:
    normalized = username.strip()
    if not _USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("username must contain only letters, numbers, underscores, or hyphens")
    return normalized.casefold()
