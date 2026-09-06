"""Typed runtime configuration for the Letterboxd MCP server."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path


_ENV_PREFIX = "LETTERBOXD_MCP_"


@dataclass(frozen=True, slots=True)
class Settings:
    """Application settings with safe local defaults."""

    base_url: str = "https://letterboxd.com"
    database_path: Path = Path("server.db")
    user_agent: str = (
        "Mozilla/5.0 (compatible; LetterboxdMCP/0.1; "
        "+https://github.com/GuptaJiHardik/movie-mcp-server)"
    )
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 20.0
    max_retries: int = 2
    retry_backoff_seconds: float = 0.5
    profile_ttl_seconds: int = 30 * 60
    diary_ttl_seconds: int = 10 * 60
    film_ttl_seconds: int = 24 * 60 * 60
    collection_ttl_seconds: int = 10 * 60
    popular_ttl_seconds: int = 30 * 60

    def __post_init__(self) -> None:
        normalized_base_url = self.base_url.rstrip("/")
        if not normalized_base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must use http or https")
        object.__setattr__(self, "base_url", normalized_base_url)
        object.__setattr__(self, "database_path", Path(self.database_path))

        positive_values = {
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "read_timeout_seconds": self.read_timeout_seconds,
            "profile_ttl_seconds": self.profile_ttl_seconds,
            "diary_ttl_seconds": self.diary_ttl_seconds,
            "film_ttl_seconds": self.film_ttl_seconds,
            "collection_ttl_seconds": self.collection_ttl_seconds,
            "popular_ttl_seconds": self.popular_ttl_seconds,
        }
        for name, value in positive_values.items():
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero")

        if self.max_retries < 0:
            raise ValueError("max_retries must not be negative")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must not be negative")
        if not self.user_agent.strip():
            raise ValueError("user_agent must not be empty")

    @property
    def request_timeout(self) -> tuple[float, float]:
        """Return the timeout shape accepted by ``requests``."""
        return (self.connect_timeout_seconds, self.read_timeout_seconds)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        """Build settings from an explicit mapping or the process environment."""
        values = os.environ if env is None else env
        defaults = cls()

        return cls(
            base_url=values.get(f"{_ENV_PREFIX}BASE_URL", defaults.base_url),
            database_path=Path(
                values.get(
                    f"{_ENV_PREFIX}DATABASE_PATH", str(defaults.database_path)
                )
            ),
            user_agent=values.get(f"{_ENV_PREFIX}USER_AGENT", defaults.user_agent),
            connect_timeout_seconds=_read_float(
                values, "CONNECT_TIMEOUT_SECONDS", defaults.connect_timeout_seconds
            ),
            read_timeout_seconds=_read_float(
                values, "READ_TIMEOUT_SECONDS", defaults.read_timeout_seconds
            ),
            max_retries=_read_int(values, "MAX_RETRIES", defaults.max_retries),
            retry_backoff_seconds=_read_float(
                values, "RETRY_BACKOFF_SECONDS", defaults.retry_backoff_seconds
            ),
            profile_ttl_seconds=_read_int(
                values, "PROFILE_TTL_SECONDS", defaults.profile_ttl_seconds
            ),
            diary_ttl_seconds=_read_int(
                values, "DIARY_TTL_SECONDS", defaults.diary_ttl_seconds
            ),
            film_ttl_seconds=_read_int(
                values, "FILM_TTL_SECONDS", defaults.film_ttl_seconds
            ),
            collection_ttl_seconds=_read_int(
                values, "COLLECTION_TTL_SECONDS", defaults.collection_ttl_seconds
            ),
            popular_ttl_seconds=_read_int(
                values, "POPULAR_TTL_SECONDS", defaults.popular_ttl_seconds
            ),
        )


def _read_int(values: Mapping[str, str], name: str, default: int) -> int:
    raw_value = values.get(f"{_ENV_PREFIX}{name}")
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as error:
        raise ValueError(f"{_ENV_PREFIX}{name} must be an integer") from error


def _read_float(values: Mapping[str, str], name: str, default: float) -> float:
    raw_value = values.get(f"{_ENV_PREFIX}{name}")
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError as error:
        raise ValueError(f"{_ENV_PREFIX}{name} must be a number") from error
