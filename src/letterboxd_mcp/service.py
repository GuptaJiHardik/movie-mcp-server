"""Application services coordinating public Letterboxd reads."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import re

from letterboxd_mcp.client import LetterboxdClient
from letterboxd_mcp.database.repositories import ProfileRepository
from letterboxd_mcp.errors import LetterboxdFetchError, UserNotFoundError
from letterboxd_mcp.models import Profile
from letterboxd_mcp.parsers import parse_profile


_USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_-]*\Z")


class LetterboxdService:
    """Coordinate HTTP, parsing, and persistence without UI concerns."""

    def __init__(
        self,
        client: LetterboxdClient,
        profile_repository: ProfileRepository,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.client = client
        self.profile_repository = profile_repository
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


def _normalize_username(username: str) -> str:
    normalized = username.strip()
    if not _USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("username must contain only letters, numbers, underscores, or hyphens")
    return normalized.casefold()
