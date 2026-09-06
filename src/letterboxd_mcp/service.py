"""Application services coordinating public Letterboxd reads."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
import re
from urllib.parse import urljoin

from letterboxd_mcp.client import LetterboxdClient
from letterboxd_mcp.database.repositories import (
    CacheState,
    CacheStateRepository,
    DiaryEntryRepository,
    FilmDetailsRepository,
    FilmRepository,
    ProfileRepository,
    ReviewRepository,
    UserFilmRepository,
)
from letterboxd_mcp.errors import (
    FilmNotFoundError,
    LetterboxdFetchError,
    ParseError,
    UserNotFoundError,
)
from letterboxd_mcp.models import (
    DiaryEntry,
    FilmDetails,
    Profile,
    UserReview,
    Viewing,
    WatchedFilm,
    WatchedFilmsPage,
)
from letterboxd_mcp.parsers import (
    parse_diary_page,
    parse_film_details,
    parse_profile,
    parse_review,
    parse_watched_page,
)


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
        user_film_repository: UserFilmRepository | None = None,
        film_details_repository: FilmDetailsRepository | None = None,
        review_repository: ReviewRepository | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.client = client
        self.profile_repository = profile_repository
        self.film_repository = film_repository
        self.diary_repository = diary_repository
        self.cache_repository = cache_repository
        self.user_film_repository = user_film_repository
        self.film_details_repository = film_details_repository
        self.review_repository = review_repository
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

        return self._refresh_diary(normalized_username, limit=limit, checked_at=checked_at)

    def get_films(
        self,
        username: str,
        limit: int = 10,
        offset: int = 0,
        refresh: bool = False,
    ) -> WatchedFilmsPage:
        """Return a bounded enriched page from a profile's watched collection."""
        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")
        if offset < 0:
            raise ValueError("offset must not be negative")
        if any(
            repository is None
            for repository in (
                self.film_repository,
                self.diary_repository,
                self.cache_repository,
                self.user_film_repository,
                self.film_details_repository,
                self.review_repository,
            )
        ):
            raise RuntimeError("watched-film repositories are not configured")

        normalized_username = _normalize_username(username)
        checked_at = self._clock()
        self._ensure_complete_user_snapshots(
            normalized_username,
            refresh=refresh,
            checked_at=checked_at,
        )

        assert self.user_film_repository is not None
        assert self.diary_repository is not None
        summaries = self.user_film_repository.list_for_user(
            normalized_username,
            limit=limit,
            offset=offset,
        )
        total = self.user_film_repository.count_for_user(normalized_username)
        slugs = [item.film.slug for item in summaries]
        diary_entries = self.diary_repository.list_for_user_films(
            normalized_username, slugs
        )
        entries_by_slug: dict[str, list[DiaryEntry]] = defaultdict(list)
        for entry in diary_entries:
            entries_by_slug[entry.film.slug].append(entry)

        items: list[WatchedFilm] = []
        for summary in summaries:
            film_entries = entries_by_slug[summary.film.slug]
            details = self._get_film_details(
                summary.film.slug,
                refresh=refresh,
                checked_at=checked_at,
            )
            review_url = next(
                (entry.review_url for entry in film_entries if entry.review_url),
                summary.review_url,
            )
            latest_review = self._get_review(
                normalized_username,
                summary.film.slug,
                review_url,
                refresh=refresh,
                checked_at=checked_at,
            )
            items.append(
                WatchedFilm(
                    username=normalized_username,
                    film=details,
                    user_rating=summary.rating,
                    liked=summary.liked,
                    viewings=tuple(
                        Viewing(
                            id=entry.id,
                            watched_date=entry.watched_date,
                            rating=entry.rating,
                            rewatch=entry.rewatch,
                            liked=entry.liked,
                            review_url=entry.review_url,
                        )
                        for entry in film_entries
                    ),
                    latest_review=latest_review,
                )
            )

        return WatchedFilmsPage(
            username=normalized_username,
            items=tuple(items),
            limit=limit,
            offset=offset,
            total=total,
            has_more=offset + len(items) < total,
            fetched_at=checked_at,
        )

    def _refresh_diary(
        self,
        normalized_username: str,
        *,
        limit: int | None,
        checked_at: datetime,
    ) -> list[DiaryEntry]:
        assert self.film_repository is not None
        assert self.diary_repository is not None
        path: str | None = f"/{normalized_username}/diary/"
        seen_paths: set[str] = set()
        entries: list[DiaryEntry] = []
        is_complete = False

        while path is not None and (limit is None or len(entries) < limit):
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
            remaining = None if limit is None else limit - len(entries)
            selected = list(
                parsed.entries if remaining is None else parsed.entries[:remaining]
            )
            entries.extend(selected)
            path = parsed.next_path
            is_complete = path is None and (
                remaining is None or len(parsed.entries) <= remaining
            )

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

    def _ensure_complete_user_snapshots(
        self,
        username: str,
        *,
        refresh: bool,
        checked_at: datetime,
    ) -> None:
        assert self.cache_repository is not None
        ttl = self.client.settings.collection_ttl_seconds
        if refresh or not _has_fresh_complete_state(
            self.cache_repository,
            "films",
            username,
            now=checked_at,
            ttl_seconds=ttl,
        ):
            self._refresh_watched_collection(username, checked_at=checked_at)

        if refresh or not _has_fresh_complete_state(
            self.cache_repository,
            "diary",
            username,
            now=checked_at,
            ttl_seconds=self.client.settings.diary_ttl_seconds,
        ):
            self._refresh_diary(username, limit=None, checked_at=checked_at)

    def _refresh_watched_collection(
        self, username: str, *, checked_at: datetime
    ) -> None:
        assert self.film_repository is not None
        assert self.user_film_repository is not None
        assert self.cache_repository is not None
        path: str | None = f"/{username}/films/by/added/"
        seen_paths: set[str] = set()
        films = []
        while path is not None:
            if path in seen_paths:
                raise ParseError("watched films", "pagination loop detected", url=path)
            seen_paths.add(path)
            page_url = urljoin(f"{self.client.settings.base_url}/", path)
            try:
                html = self.client.get(path)
            except LetterboxdFetchError as error:
                if error.status_code == 404:
                    raise UserNotFoundError(username) from error
                raise
            parsed = parse_watched_page(
                html,
                username=username,
                fetched_at=checked_at,
                start_position=len(films),
                url=page_url,
            )
            films.extend(parsed.films)
            path = parsed.next_path

        self.film_repository.upsert_many([item.film for item in films])
        self.user_film_repository.replace_for_user(username, films)
        state = CacheState("films", username, checked_at)
        self.cache_repository.upsert(state)
        self.cache_repository.upsert(
            CacheState("films_complete", username, checked_at)
        )

    def _get_film_details(
        self, slug: str, *, refresh: bool, checked_at: datetime
    ) -> FilmDetails:
        assert self.film_repository is not None
        assert self.film_details_repository is not None
        assert self.cache_repository is not None
        cached = self.film_details_repository.get(slug)
        state = self.cache_repository.get("film", slug)
        if not refresh and cached is not None and _is_fresh(
            state,
            now=checked_at,
            ttl_seconds=self.client.settings.film_ttl_seconds,
        ):
            return cached

        path = f"/film/{slug}/"
        page_url = urljoin(f"{self.client.settings.base_url}/", path)
        try:
            html = self.client.get(path)
        except LetterboxdFetchError as error:
            if error.status_code == 404:
                raise FilmNotFoundError(slug) from error
            raise
        details = parse_film_details(
            html, slug=slug, fetched_at=checked_at, url=page_url
        )
        self.film_repository.upsert_many([details])
        self.film_details_repository.replace(details)
        self.cache_repository.upsert(CacheState("film", slug, checked_at))
        return details

    def _get_review(
        self,
        username: str,
        film_slug: str,
        review_url: str | None,
        *,
        refresh: bool,
        checked_at: datetime,
    ) -> UserReview | None:
        if review_url is None:
            return None
        assert self.review_repository is not None
        assert self.cache_repository is not None
        cached = self.review_repository.get_by_url(review_url)
        state = self.cache_repository.get("review", review_url)
        if not refresh and cached is not None and _is_fresh(
            state,
            now=checked_at,
            ttl_seconds=self.client.settings.collection_ttl_seconds,
        ):
            return cached

        page_url = urljoin(f"{self.client.settings.base_url}/", review_url)
        html = self.client.get(review_url)
        review = parse_review(
            html,
            username=username,
            film_slug=film_slug,
            review_url=review_url,
            fetched_at=checked_at,
            url=page_url,
        )
        self.review_repository.upsert(review)
        self.cache_repository.upsert(CacheState("review", review_url, checked_at))
        return review


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


def _has_fresh_complete_state(
    repository: CacheStateRepository,
    resource_type: str,
    resource_key: str,
    *,
    now: datetime,
    ttl_seconds: int,
) -> bool:
    state = repository.get(resource_type, resource_key)
    complete = repository.get(f"{resource_type}_complete", resource_key)
    return (
        state is not None
        and complete is not None
        and state.fetched_at == complete.fetched_at
        and _is_fresh(state, now=now, ttl_seconds=ttl_seconds)
    )
