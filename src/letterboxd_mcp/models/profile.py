"""Typed public profile data."""

from __future__ import annotations

from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Profile(BaseModel):
    """A normalized public Letterboxd profile."""

    model_config = ConfigDict(frozen=True)

    username: NonEmptyString
    display_name: NonEmptyString
    bio: str | None = None
    avatar_url: str | None = None
    films_count: int | None = Field(default=None, ge=0)
    followers_count: int | None = Field(default=None, ge=0)
    following_count: int | None = Field(default=None, ge=0)
    fetched_at: AwareDatetime
