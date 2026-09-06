"""Persistence adapters for normalized Letterboxd resources."""

from letterboxd_mcp.database.repositories.cache_state import (
    CacheState,
    CacheStateRepository,
)
from letterboxd_mcp.database.repositories.diary_entries import DiaryEntryRepository
from letterboxd_mcp.database.repositories.film_details import FilmDetailsRepository
from letterboxd_mcp.database.repositories.films import FilmRepository
from letterboxd_mcp.database.repositories.profiles import ProfileRepository
from letterboxd_mcp.database.repositories.reviews import ReviewRepository
from letterboxd_mcp.database.repositories.user_films import UserFilmRepository

__all__ = [
    "CacheState",
    "CacheStateRepository",
    "DiaryEntryRepository",
    "FilmDetailsRepository",
    "FilmRepository",
    "ProfileRepository",
    "ReviewRepository",
    "UserFilmRepository",
]
