"""Structured domain errors exposed by the Letterboxd MCP layers."""

from __future__ import annotations


class LetterboxdError(Exception):
    """Base class for expected Letterboxd MCP failures."""


class UserNotFoundError(LetterboxdError):
    """Raised when a public Letterboxd user cannot be found."""

    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"Letterboxd user not found: {username}")


class FilmNotFoundError(LetterboxdError):
    """Raised when a Letterboxd film cannot be found."""

    def __init__(self, film_slug: str) -> None:
        self.film_slug = film_slug
        super().__init__(f"Letterboxd film not found: {film_slug}")


class LetterboxdFetchError(LetterboxdError):
    """Raised when Letterboxd HTML cannot be fetched successfully."""

    def __init__(
        self,
        url: str,
        message: str = "Unable to fetch Letterboxd page",
        *,
        status_code: int | None = None,
    ) -> None:
        self.url = url
        self.status_code = status_code
        status_suffix = f" (HTTP {status_code})" if status_code is not None else ""
        super().__init__(f"{message}{status_suffix}: {url}")


class ChallengePageError(LetterboxdFetchError):
    """Raised when Letterboxd responds with a challenge or CAPTCHA page."""

    def __init__(self, url: str, *, status_code: int | None = None) -> None:
        super().__init__(
            url,
            "Letterboxd returned a challenge page",
            status_code=status_code,
        )


class ParseError(LetterboxdError):
    """Raised when expected data cannot be parsed from fetched HTML."""

    def __init__(self, page_type: str, message: str, *, url: str | None = None) -> None:
        self.page_type = page_type
        self.url = url
        location = f" at {url}" if url is not None else ""
        super().__init__(f"Unable to parse {page_type} page{location}: {message}")


class DatabaseError(LetterboxdError):
    """Raised when a database operation fails."""

    def __init__(self, operation: str, message: str = "Database operation failed") -> None:
        self.operation = operation
        super().__init__(f"{message}: {operation}")
