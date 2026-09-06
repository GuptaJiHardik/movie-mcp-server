"""Polite HTTP access to public Letterboxd pages."""

from __future__ import annotations

from collections.abc import Callable
import time
from urllib.parse import urljoin, urlsplit

import requests

from letterboxd_mcp.config import Settings
from letterboxd_mcp.errors import ChallengePageError, LetterboxdFetchError


_TRANSIENT_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_CHALLENGE_MARKERS = (
    "cf-chl-",
    "challenge-platform",
    "just a moment...</title>",
    "attention required! | cloudflare",
    "verify you are human",
    "captcha-container",
    "g-recaptcha",
    "h-captcha",
)
_MAX_RETRY_AFTER_SECONDS = 60.0


class LetterboxdClient:
    """Fetch HTML with one reusable session and bounded retries."""

    def __init__(
        self,
        settings: Settings,
        *,
        session: requests.Session | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self._sleeper = sleeper
        self.session.headers.update(
            {
                "User-Agent": settings.user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.8",
            }
        )

    def get(self, path_or_url: str) -> str:
        """Fetch a Letterboxd path or URL and return decoded HTML."""
        url = self._resolve_url(path_or_url)

        for attempt in range(self.settings.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.settings.request_timeout)
            except (requests.ConnectionError, requests.Timeout) as error:
                if attempt < self.settings.max_retries:
                    self._sleeper(self._backoff(attempt))
                    continue
                raise LetterboxdFetchError(url, str(error)) from error
            except requests.RequestException as error:
                raise LetterboxdFetchError(url, str(error)) from error

            try:
                if response.url and not self._is_configured_origin(response.url):
                    raise LetterboxdFetchError(
                        url,
                        "Letterboxd redirected to an untrusted origin",
                        status_code=response.status_code,
                    )

                html = self._decode_html(response)
                if self._is_challenge(response, html):
                    raise ChallengePageError(url, status_code=response.status_code)

                if response.status_code in _TRANSIENT_STATUS_CODES:
                    if attempt < self.settings.max_retries:
                        self._sleeper(self._retry_delay(response, attempt))
                        continue
                    raise LetterboxdFetchError(
                        url,
                        "Letterboxd returned a transient error after retries",
                        status_code=response.status_code,
                    )

                if response.status_code >= 400:
                    raise LetterboxdFetchError(
                        url,
                        "Letterboxd returned an HTTP error",
                        status_code=response.status_code,
                    )

                return html
            finally:
                response.close()

        raise AssertionError("retry loop exited unexpectedly")

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self) -> LetterboxdClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _resolve_url(self, path_or_url: str) -> str:
        if not path_or_url.strip():
            raise ValueError("path_or_url must not be empty")

        url = urljoin(f"{self.settings.base_url}/", path_or_url)
        if not self._is_configured_origin(url):
            raise ValueError("LetterboxdClient only fetches URLs from its configured origin")
        return url

    def _is_configured_origin(self, url: str) -> bool:
        base_parts = urlsplit(self.settings.base_url)
        url_parts = urlsplit(url)
        return (url_parts.scheme, url_parts.netloc) == (
            base_parts.scheme,
            base_parts.netloc,
        )

    def _decode_html(self, response: requests.Response) -> str:
        content_type = response.headers.get("Content-Type", "").lower()
        if "charset=" not in content_type:
            response.encoding = "utf-8"
        return response.text

    def _is_challenge(self, response: requests.Response, html: str) -> bool:
        if response.headers.get("cf-mitigated", "").lower() == "challenge":
            return True
        lowered_html = html[:200_000].lower()
        return any(marker in lowered_html for marker in _CHALLENGE_MARKERS)

    def _retry_delay(self, response: requests.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return max(0.0, min(float(retry_after), _MAX_RETRY_AFTER_SECONDS))
            except ValueError:
                pass
        return self._backoff(attempt)

    def _backoff(self, attempt: int) -> float:
        return self.settings.retry_backoff_seconds * (2**attempt)
