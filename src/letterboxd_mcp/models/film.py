"""Typed film summaries used by collection reads."""

from __future__ import annotations

from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Film(BaseModel):
    """A normalized Letterboxd film identity and summary."""

    model_config = ConfigDict(frozen=True)

    slug: NonEmptyString
    title: NonEmptyString
    year: int | None = Field(default=None, ge=1870)
    url: NonEmptyString
    poster_url: str | None = None
    fetched_at: AwareDatetime
