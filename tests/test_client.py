from __future__ import annotations

from unittest.mock import Mock

import pytest
import requests

from letterboxd_mcp.client import LetterboxdClient
from letterboxd_mcp.config import Settings
from letterboxd_mcp.errors import ChallengePageError, LetterboxdFetchError


def make_response(
    status_code: int = 200,
    html: str = "<html><title>Letterboxd</title></html>",
    *,
    headers: dict[str, str] | None = None,
) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = html.encode("utf-8")
    response._content_consumed = True
    response.headers.update(headers or {})
    response.url = "https://letterboxd.com/test/"
    return response


@pytest.fixture
def session() -> requests.Session:
    return requests.Session()


def test_reuses_session_and_sends_explicit_headers_and_timeout(session) -> None:
    session.get = Mock(side_effect=[make_response(), make_response()])
    settings = Settings(user_agent="letterboxd-test-agent")
    client = LetterboxdClient(settings, session=session)

    assert client.get("/alice/").startswith("<html>")
    assert client.get("/alice/films/").startswith("<html>")

    assert session.get.call_count == 2
    session.get.assert_any_call(
        "https://letterboxd.com/alice/", timeout=(5.0, 20.0)
    )
    assert session.headers["User-Agent"] == "letterboxd-test-agent"
    assert session.headers["Accept"].startswith("text/html")


def test_decodes_utf8_when_response_has_no_declared_charset(session) -> None:
    session.get = Mock(return_value=make_response(html="<p>Amélie</p>"))
    client = LetterboxdClient(Settings(), session=session)

    assert client.get("/film/amelie/") == "<p>Amélie</p>"


def test_retries_transient_status_with_exponential_backoff(session) -> None:
    session.get = Mock(side_effect=[make_response(503), make_response(200)])
    sleeper = Mock()
    client = LetterboxdClient(Settings(), session=session, sleeper=sleeper)

    assert "Letterboxd" in client.get("/alice/")

    sleeper.assert_called_once_with(0.5)
    assert session.get.call_count == 2


def test_respects_bounded_numeric_retry_after(session) -> None:
    session.get = Mock(
        side_effect=[
            make_response(429, headers={"Retry-After": "500"}),
            make_response(200),
        ]
    )
    sleeper = Mock()
    client = LetterboxdClient(Settings(), session=session, sleeper=sleeper)

    client.get("/alice/")

    sleeper.assert_called_once_with(60.0)


def test_exhausted_transient_response_raises_structured_error(session) -> None:
    session.get = Mock(side_effect=[make_response(503), make_response(503)])
    client = LetterboxdClient(
        Settings(max_retries=1), session=session, sleeper=Mock()
    )

    with pytest.raises(LetterboxdFetchError) as captured:
        client.get("/alice/")

    assert captured.value.status_code == 503
    assert captured.value.url == "https://letterboxd.com/alice/"


def test_retries_timeout_and_preserves_final_cause(session) -> None:
    timeout = requests.Timeout("read timed out")
    session.get = Mock(side_effect=[timeout, timeout])
    sleeper = Mock()
    client = LetterboxdClient(
        Settings(max_retries=1), session=session, sleeper=sleeper
    )

    with pytest.raises(LetterboxdFetchError) as captured:
        client.get("/alice/")

    assert captured.value.__cause__ is timeout
    sleeper.assert_called_once_with(0.5)


@pytest.mark.parametrize(
    "response",
    [
        make_response(403, headers={"cf-mitigated": "challenge"}),
        make_response(200, "<html><title>Just a moment...</title></html>"),
        make_response(200, "<div class='g-recaptcha'></div>"),
    ],
)
def test_detects_challenge_without_retrying(session, response) -> None:
    session.get = Mock(return_value=response)
    sleeper = Mock()
    client = LetterboxdClient(Settings(), session=session, sleeper=sleeper)

    with pytest.raises(ChallengePageError):
        client.get("/alice/")

    session.get.assert_called_once()
    sleeper.assert_not_called()


def test_non_transient_http_error_is_not_retried(session) -> None:
    session.get = Mock(return_value=make_response(404))
    client = LetterboxdClient(Settings(), session=session, sleeper=Mock())

    with pytest.raises(LetterboxdFetchError) as captured:
        client.get("/missing/")

    assert captured.value.status_code == 404
    session.get.assert_called_once()


def test_rejects_redirect_to_untrusted_origin(session) -> None:
    response = make_response()
    response.url = "https://example.com/captured/"
    session.get = Mock(return_value=response)
    client = LetterboxdClient(Settings(), session=session)

    with pytest.raises(LetterboxdFetchError, match="untrusted origin"):
        client.get("/alice/")


def test_negative_retry_after_is_clamped_to_zero(session) -> None:
    session.get = Mock(
        side_effect=[
            make_response(429, headers={"Retry-After": "-5"}),
            make_response(200),
        ]
    )
    sleeper = Mock()
    client = LetterboxdClient(Settings(), session=session, sleeper=sleeper)

    client.get("/alice/")

    sleeper.assert_called_once_with(0.0)


@pytest.mark.parametrize(
    "url",
    ["https://example.com/film/arrival/", "//example.com/film/arrival/", ""],
)
def test_rejects_empty_or_cross_origin_urls_without_request(session, url) -> None:
    session.get = Mock()
    client = LetterboxdClient(Settings(), session=session)

    with pytest.raises(ValueError):
        client.get(url)

    session.get.assert_not_called()


def test_context_manager_closes_session(session) -> None:
    session.close = Mock()

    with LetterboxdClient(Settings(), session=session):
        pass

    session.close.assert_called_once_with()
