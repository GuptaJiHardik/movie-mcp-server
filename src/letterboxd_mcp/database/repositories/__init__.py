"""Persistence adapters for normalized Letterboxd resources."""

from letterboxd_mcp.database.repositories.cache_state import (
    CacheState,
    CacheStateRepository,
)
from letterboxd_mcp.database.repositories.diary_entries import DiaryEntryRepository
from letterboxd_mcp.database.repositories.films import FilmRepository
from letterboxd_mcp.database.repositories.profiles import ProfileRepository

__all__ = [
    "CacheState",
    "CacheStateRepository",
    "DiaryEntryRepository",
    "FilmRepository",
    "ProfileRepository",
]
