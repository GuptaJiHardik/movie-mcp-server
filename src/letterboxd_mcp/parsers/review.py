"""Parser for one profile-authored public Letterboxd review."""

from __future__ import annotations

from datetime import date, datetime
import json
import re

from bs4 import BeautifulSoup
from pydantic import ValidationError

from letterboxd_mcp.errors import ParseError
from letterboxd_mcp.models import UserReview


_VIEWING_ID = re.compile(r"viewing:(\d+)")


def parse_review(
    html: str,
    *,
    username: str,
    film_slug: str,
    review_url: str,
    fetched_at: datetime,
    url: str | None = None,
) -> UserReview:
    """Parse a profile's public review page."""
    soup = BeautifulSoup(html, "html.parser")
    review = soup.select_one("section.review.js-review")
    body = review.select_one(".js-review-body") if review is not None else None
    if review is None or body is None:
        raise ParseError("review", "missing public review", url=url)

    try:
        text = body.get_text("\n", strip=True)
        if not text:
            raise ValueError("missing review text")
        identifier = review.select_one("[data-likeable-identifier]")
        review_id = _review_id(identifier.get("data-likeable-identifier") if identifier else None)
        rating_meta = soup.select_one("meta[name='twitter:data2']")
        rating = _rating(rating_meta.get("content") if rating_meta else None)
        view_date = review.select_one(".view-date")
        return UserReview(
            id=review_id or review_url,
            username=username,
            film_slug=film_slug,
            review_url=review_url,
            reviewed_date=_date_from_links(view_date),
            rating=rating,
            liked=review.select_one(".content-reactions-strip .inline-liked") is not None,
            contains_spoilers=(
                review.select_one(".js-spoiler") is not None
                or "may contain spoilers" in review.get_text(" ", strip=True).casefold()
            ),
            review_text=text,
            fetched_at=fetched_at,
        )
    except (ValueError, TypeError, json.JSONDecodeError, ValidationError) as error:
        raise ParseError("review", str(error), url=url) from error


def _review_id(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        match = _VIEWING_ID.search(raw)
        return match.group(1) if match else None
    uid = payload.get("uid") if isinstance(payload, dict) else None
    match = _VIEWING_ID.search(uid) if isinstance(uid, str) else None
    return match.group(1) if match else None


def _rating(raw: object) -> float | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    value = raw.strip()
    if not set(value) <= {"★", "½"} or value.count("½") > 1:
        return None
    return float(value.count("★")) + (0.5 if "½" in value else 0.0)


def _date_from_links(element: object) -> date | None:
    if not hasattr(element, "select"):
        return None
    for link in element.select("a[href]"):
        match = re.search(r"/for/(\d{4})/(\d{2})/(\d{2})/", link.get("href", ""))
        if match:
            return date(*(int(part) for part in match.groups()))
    return None
