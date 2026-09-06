"""Typed public diary entries."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from letterboxd_mcp.models.film import Film


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DiaryEntry(BaseModel):
    """One normalized public Letterboxd diary entry."""

    model_config = ConfigDict(frozen=True)

    id: NonEmptyString
    username: NonEmptyString
    film: Film
    watched_date: date
    rating: float | None = Field(default=None, ge=0.5, le=5.0)
    rewatch: bool = False
    liked: bool | None = None
    review_url: str | None = None
    fetched_at: AwareDatetime
