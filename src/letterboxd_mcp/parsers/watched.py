"""Parser for a profile's public watched-films collection pages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

from bs4 import BeautifulSoup, Tag
from pydantic import ValidationError

from letterboxd_mcp.errors import ParseError
from letterboxd_mcp.models import Film, UserFilm


_DISPLAY_NAME = re.compile(r"(?P<title>.+?)(?: \((?P<year>\d{4})\))?\Z")
_RATED_CLASS = re.compile(r"rated-(\d+)\Z")


@dataclass(frozen=True, slots=True)
class ParsedWatchedPage:
    """Normalized watched titles plus the site's real next-page path."""

    films: tuple[UserFilm, ...]
    next_path: str | None


def parse_watched_page(
    html: str,
    *,
    username: str,
    fetched_at: datetime,
    start_position: int = 0,
    url: str | None = None,
) -> ParsedWatchedPage:
    """Parse one watched-films page without network access."""
    soup = BeautifulSoup(html, "html.parser")
    grid = soup.select_one(".poster-grid")
    if grid is None:
        raise ParseError("watched films", "missing poster grid", url=url)

    films = tuple(
        _parse_item(
            item,
            username=username,
            fetched_at=fetched_at,
            position=start_position + position,
            url=url,
        )
        for position, item in enumerate(grid.select("li.griditem"))
    )
    next_link = soup.select_one(".pagination a.next[href]")
    return ParsedWatchedPage(
        films=films,
        next_path=_optional_attribute(next_link, "href"),
    )


def _parse_item(
    item: Tag,
    *,
    username: str,
    fetched_at: datetime,
    position: int,
    url: str | None,
) -> UserFilm:
    try:
        poster = item.select_one("[data-item-slug]")
        slug = _required_attribute(poster, "data-item-slug", "film slug")
        path = _optional_attribute(poster, "data-item-link") or f"/film/{slug}/"
        display_name = (
            _optional_attribute(poster, "data-item-full-display-name")
            or _required_attribute(poster, "data-item-name", "film title")
        )
        match = _DISPLAY_NAME.fullmatch(display_name)
        if match is None:
            raise ValueError("invalid film display name")
        title = match.group("title").strip()
        year = int(match.group("year")) if match.group("year") else None
        image = poster.select_one("img") if poster is not None else None
        poster_url = _optional_attribute(image, "data-src") or _optional_attribute(
            image, "src"
        )
        if poster_url and "/static/img/empty-poster-" in poster_url:
            poster_url = None

        rating_element = item.select_one(".poster-viewingdata .rating")
        review = item.select_one(".poster-viewingdata a.review-micro[href]")
        return UserFilm(
            username=username,
            film=Film(
                slug=slug,
                title=title,
                year=year,
                url=path,
                poster_url=poster_url,
                fetched_at=fetched_at,
            ),
            position=position,
            rating=_parse_rating(rating_element),
            liked=item.select_one(".poster-viewingdata .liked-micro") is not None,
            review_url=_optional_attribute(review, "href"),
            fetched_at=fetched_at,
        )
    except (ValueError, ValidationError) as error:
        raise ParseError("watched films", str(error), url=url) from error


def _parse_rating(element: Tag | None) -> float | None:
    if element is None:
        return None
    for class_name in element.get("class", []):
        match = _RATED_CLASS.fullmatch(str(class_name))
        if match is not None:
            half_stars = int(match.group(1))
            return None if half_stars == 0 else half_stars / 2
    return None


def _required_attribute(element: Tag | None, name: str, description: str) -> str:
    value = _optional_attribute(element, name)
    if value is None:
        raise ValueError(f"missing {description}")
    return value


def _optional_attribute(element: Tag | None, name: str) -> str | None:
    if element is None:
        return None
    value = element.get(name)
    if not isinstance(value, str):
        return None
    return value.strip() or None
