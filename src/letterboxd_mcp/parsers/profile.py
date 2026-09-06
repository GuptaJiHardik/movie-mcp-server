"""Parser for public Letterboxd profile pages."""

from __future__ import annotations

from datetime import datetime
import re

from bs4 import BeautifulSoup, Tag

from letterboxd_mcp.errors import ParseError
from letterboxd_mcp.models import Profile


_COUNT_PATTERN = re.compile(r"\d[\d,]*\Z")


def parse_profile(
    html: str,
    *,
    username: str,
    fetched_at: datetime,
    url: str | None = None,
) -> Profile:
    """Parse one fetched profile page into normalized data."""
    soup = BeautifulSoup(html, "html.parser")
    header = soup.select_one("section.profile-header[data-person]")
    if header is None:
        raise ParseError("profile", "missing profile header", url=url)

    name_element = header.select_one(".profile-name-and-actions h1")
    display_name = _direct_text(name_element)
    if display_name is None:
        raise ParseError("profile", "missing display name", url=url)

    statistics = _parse_statistics(header)
    avatar = header.select_one(".profile-avatar img[src]")
    bio_element = soup.select_one(
        ".profile-person-bio .body-text, .profile-person-bio .prose"
    )

    return Profile(
        username=username,
        display_name=display_name,
        bio=_optional_text(bio_element, separator="\n"),
        avatar_url=_optional_attribute(avatar, "src"),
        films_count=statistics.get("films"),
        followers_count=statistics.get("followers"),
        following_count=statistics.get("following"),
        fetched_at=fetched_at,
    )


def _parse_statistics(header: Tag) -> dict[str, int]:
    statistics: dict[str, int] = {}
    for statistic in header.select(".profile-stats .profile-statistic"):
        definition = statistic.select_one(".definition")
        value = statistic.select_one(".value")
        if definition is None or value is None:
            continue

        label = definition.get_text(" ", strip=True).casefold()
        raw_value = value.get_text(" ", strip=True)
        match = _COUNT_PATTERN.fullmatch(raw_value)
        if label in {"films", "followers", "following"} and match is not None:
            statistics[label] = int(match.group().replace(",", ""))
    return statistics


def _direct_text(element: Tag | None) -> str | None:
    if element is None:
        return None
    for child in element.children:
        if isinstance(child, str) and child.strip():
            return child.strip()
    return _optional_text(element)


def _optional_text(element: Tag | None, *, separator: str = " ") -> str | None:
    if element is None:
        return None
    value = element.get_text(separator, strip=True)
    return value or None


def _optional_attribute(element: Tag | None, name: str) -> str | None:
    if element is None:
        return None
    value = element.get(name)
    if not isinstance(value, str):
        return None
    return value.strip() or None
