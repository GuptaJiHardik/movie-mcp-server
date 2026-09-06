"""Parser for public Letterboxd diary pages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re

from bs4 import BeautifulSoup, Tag
from pydantic import ValidationError

from letterboxd_mcp.errors import ParseError
from letterboxd_mcp.models import DiaryEntry, Film


_DATE_PATH = re.compile(r"/for/(\d{4})/(\d{2})/(\d{2})/")
_RATED_CLASS = re.compile(r"rated-(\d+)\Z")
_INTEGER = re.compile(r"\d+\Z")


@dataclass(frozen=True, slots=True)
class ParsedDiaryPage:
    """Normalized diary rows plus the site's real next-page path."""

    entries: tuple[DiaryEntry, ...]
    next_path: str | None


def parse_diary_page(
    html: str,
    *,
    username: str,
    fetched_at: datetime,
    url: str | None = None,
) -> ParsedDiaryPage:
    """Parse one diary page without performing any network access."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table#diary-table.diary-table")
    if table is None:
        raise ParseError("diary", "missing diary table", url=url)

    entries = tuple(
        _parse_row(row, username=username, fetched_at=fetched_at, url=url)
        for row in table.select("tr.diary-entry-row")
    )
    next_link = soup.select_one(".pagination a.next[href]")
    next_path = _optional_attribute(next_link, "href")
    return ParsedDiaryPage(entries=entries, next_path=next_path)


def _parse_row(
    row: Tag,
    *,
    username: str,
    fetched_at: datetime,
    url: str | None,
) -> DiaryEntry:
    try:
        entry_id = _required_attribute(row, "data-viewing-id", "viewing ID")
        figure = row.select_one(".col-production [data-item-slug]")
        if figure is None:
            raise ValueError("missing film identity")
        slug = _required_attribute(figure, "data-item-slug", "film slug")

        title_element = row.select_one(".col-production h2.primaryname a")
        title = _required_text(title_element, "film title")
        watched_date = _parse_watched_date(row)
        year = _parse_year(row)
        poster_url = _parse_poster_url(figure)

        film = Film(
            slug=slug,
            title=title,
            year=year,
            url=f"/film/{slug}/",
            poster_url=poster_url,
            fetched_at=fetched_at,
        )
        return DiaryEntry(
            id=entry_id,
            username=username,
            film=film,
            watched_date=watched_date,
            rating=_parse_rating(row),
            rewatch=_status_value(row.select_one(".col-rewatch"), default=False),
            liked=_parse_liked(row),
            review_url=_parse_review_url(row),
            fetched_at=fetched_at,
        )
    except (ValueError, ValidationError) as error:
        raise ParseError("diary", str(error), url=url) from error


def _parse_watched_date(row: Tag) -> date:
    day_link = row.select_one(".col-daydate a.daydate[href]")
    href = _required_attribute(day_link, "href", "watched date")
    match = _DATE_PATH.search(href)
    if match is None:
        raise ValueError("invalid watched date")
    return date(*(int(part) for part in match.groups()))


def _parse_year(row: Tag) -> int | None:
    element = row.select_one(".col-releaseyear")
    if element is None:
        return None
    value = element.get_text(" ", strip=True)
    if not value:
        return None
    if _INTEGER.fullmatch(value) is None:
        raise ValueError("invalid film year")
    return int(value)


def _parse_rating(row: Tag) -> float | None:
    element = row.select_one(".col-rating .rating")
    if element is None:
        return None
    for class_name in element.get("class", []):
        match = _RATED_CLASS.fullmatch(str(class_name))
        if match is not None:
            half_stars = int(match.group(1))
            if half_stars == 0:
                return None
            return half_stars / 2

    symbols = element.get_text("", strip=True)
    if not symbols:
        return None
    if set(symbols) <= {"★", "½"} and symbols.count("½") <= 1:
        return float(symbols.count("★")) + (0.5 if "½" in symbols else 0.0)
    raise ValueError("invalid rating")


def _status_value(element: Tag | None, *, default: bool | None) -> bool | None:
    if element is None:
        return default
    classes = set(element.get("class", []))
    if "icon-status-on" in classes:
        return True
    if "icon-status-off" in classes:
        return False
    return default


def _parse_liked(row: Tag) -> bool | None:
    element = row.select_one(".col-like")
    if element is None:
        return None
    return element.select_one(".icon-liked") is not None


def _parse_review_url(row: Tag) -> str | None:
    link = row.select_one(".col-review a[href]")
    return _optional_attribute(link, "href")


def _parse_poster_url(figure: Tag) -> str | None:
    image = figure.select_one("img")
    if image is None:
        return None
    candidate = _optional_attribute(image, "data-src") or _optional_attribute(
        image, "src"
    )
    if candidate is None or "/static/img/empty-poster-" in candidate:
        return None
    return candidate


def _required_text(element: Tag | None, description: str) -> str:
    if element is None:
        raise ValueError(f"missing {description}")
    value = element.get_text(" ", strip=True)
    if not value:
        raise ValueError(f"missing {description}")
    return value


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
