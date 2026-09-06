"""Typed enriched watched-film data returned by the MCP server."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from letterboxd_mcp.models.film import Film


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CastMember(BaseModel):
    """One billed cast member from a public film page."""

    model_config = ConfigDict(frozen=True)

    name: NonEmptyString
    role: str | None = None
    url: str | None = None


class FilmDetails(Film):
    """A film summary enriched with public film-page metadata."""

    original_title: str | None = None
    tagline: str | None = None
    synopsis: str | None = None
    runtime_minutes: int | None = Field(default=None, gt=0)
    directors: tuple[NonEmptyString, ...] = ()
    genres: tuple[NonEmptyString, ...] = ()
    cast: tuple[CastMember, ...] = ()
    average_rating: float | None = Field(default=None, ge=0.5, le=5.0)


class UserFilm(BaseModel):
    """One title in a profile's unique public watched collection."""

    model_config = ConfigDict(frozen=True)

    username: NonEmptyString
    film: Film
    position: int = Field(ge=0)
    rating: float | None = Field(default=None, ge=0.5, le=5.0)
    liked: bool = False
    review_url: str | None = None
    fetched_at: AwareDatetime


class Viewing(BaseModel):
    """One dated public diary viewing nested beneath a watched film."""

    model_config = ConfigDict(frozen=True)

    id: NonEmptyString
    watched_date: date
    rating: float | None = Field(default=None, ge=0.5, le=5.0)
    rewatch: bool = False
    liked: bool | None = None
    review_url: str | None = None


class UserReview(BaseModel):
    """The profile's latest public review for a film."""

    model_config = ConfigDict(frozen=True)

    id: NonEmptyString
    username: NonEmptyString
    film_slug: NonEmptyString
    review_url: NonEmptyString
    reviewed_date: date | None = None
    rating: float | None = Field(default=None, ge=0.5, le=5.0)
    liked: bool = False
    contains_spoilers: bool = False
    review_text: NonEmptyString
    fetched_at: AwareDatetime


class WatchedFilm(BaseModel):
    """One enriched title from a profile's watched collection."""

    model_config = ConfigDict(frozen=True)

    username: NonEmptyString
    film: FilmDetails
    user_rating: float | None = Field(default=None, ge=0.5, le=5.0)
    liked: bool = False
    viewings: tuple[Viewing, ...] = ()
    latest_review: UserReview | None = None


class WatchedFilmsPage(BaseModel):
    """A bounded page of enriched watched titles."""

    model_config = ConfigDict(frozen=True)

    username: NonEmptyString
    items: tuple[WatchedFilm, ...]
    limit: int = Field(ge=1, le=20)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
    has_more: bool
    fetched_at: AwareDatetime
