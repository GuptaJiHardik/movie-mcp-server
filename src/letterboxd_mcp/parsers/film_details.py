"""Parser for public Letterboxd film detail pages."""

from __future__ import annotations

from datetime import datetime
import json
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from pydantic import ValidationError

from letterboxd_mcp.errors import ParseError
from letterboxd_mcp.models import CastMember, FilmDetails


_DURATION = re.compile(r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?\Z")


def parse_film_details(
    html: str,
    *,
    slug: str,
    fetched_at: datetime,
    url: str | None = None,
) -> FilmDetails:
    """Parse normalized metadata from one public film page."""
    soup = BeautifulSoup(html, "html.parser")
    script = soup.select_one("script[type='application/ld+json']")
    if script is None or script.string is None:
        raise ParseError("film", "missing structured film data", url=url)

    try:
        raw = script.string
        payload = json.loads(raw[raw.index("{") : raw.rindex("}") + 1])
        if payload.get("@type") != "Movie":
            raise ValueError("structured data is not a movie")
        title = _required_string(payload.get("name"), "film title")
        year = _year(payload.get("dateCreated"))
        directors = tuple(
            name
            for item in _as_list(payload.get("director"))
            if isinstance(item, dict)
            and (name := _optional_string(item.get("name"))) is not None
        )
        genres = tuple(
            value
            for item in _as_list(payload.get("genre"))
            if (value := _optional_string(item)) is not None
        )
        roles = {
            link.get_text(" ", strip=True): _optional_string(link.get("title"))
            for link in soup.select("#tab-panel-cast .cast-list a[href]")
        }
        cast = tuple(
            CastMember(
                name=name,
                role=roles.get(name),
                url=_relative_url(_optional_string(item.get("sameAs"))),
            )
            for item in _as_list(payload.get("actor"))[:10]
            if isinstance(item, dict)
            and (name := _optional_string(item.get("name"))) is not None
        )
        aggregate = payload.get("aggregateRating")
        average_rating = (
            float(aggregate["ratingValue"])
            if isinstance(aggregate, dict) and aggregate.get("ratingValue") is not None
            else None
        )
        original = soup.select_one(".originalname")
        tagline = soup.select_one(".tagline")

        return FilmDetails(
            slug=slug,
            title=title,
            year=year,
            url=f"/film/{slug}/",
            poster_url=_optional_string(payload.get("image")),
            fetched_at=fetched_at,
            original_title=_optional_text(original),
            tagline=_optional_text(tagline),
            synopsis=_optional_string(payload.get("description")),
            runtime_minutes=_runtime_minutes(payload.get("duration")),
            directors=directors,
            genres=genres,
            cast=cast,
            average_rating=average_rating,
        )
    except (ValueError, TypeError, json.JSONDecodeError, ValidationError) as error:
        raise ParseError("film", str(error), url=url) from error


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    return [] if value is None else [value]


def _required_string(value: object, description: str) -> str:
    result = _optional_string(value)
    if result is None:
        raise ValueError(f"missing {description}")
    return result


def _optional_string(value: object) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _optional_text(element: object) -> str | None:
    if not hasattr(element, "get_text"):
        return None
    value = element.get_text(" ", strip=True)
    return value or None


def _year(value: object) -> int | None:
    text = _optional_string(value)
    return int(text[:4]) if text and re.match(r"\d{4}", text) else None


def _runtime_minutes(value: object) -> int | None:
    text = _optional_string(value)
    if text is None:
        return None
    match = _DURATION.fullmatch(text)
    if match is None:
        raise ValueError("invalid film duration")
    return int(match.group("hours") or 0) * 60 + int(match.group("minutes") or 0)


def _relative_url(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = urlparse(value)
    return parsed.path if parsed.netloc.endswith("letterboxd.com") else value
