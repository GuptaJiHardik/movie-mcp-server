"""Local stdio FastMCP runtime and console entry point."""

from fastmcp import FastMCP

from letterboxd_mcp.client import LetterboxdClient
from letterboxd_mcp.config import Settings
from letterboxd_mcp.database import Database
from letterboxd_mcp.database.repositories import (
    CacheStateRepository,
    DiaryEntryRepository,
    FilmRepository,
    ProfileRepository,
)
from letterboxd_mcp.service import LetterboxdService
from letterboxd_mcp.tools import register_diary_tool, register_profile_tool


def create_mcp(service: LetterboxdService) -> FastMCP:
    """Create the MCP server around an injected application service."""
    mcp = FastMCP(
        "Letterboxd MCP",
        instructions="Read-only access to public Letterboxd profiles and diaries.",
    )
    register_profile_tool(mcp, service)
    register_diary_tool(mcp, service)
    return mcp


def main() -> None:
    """Initialize local dependencies and run the MCP server over stdio."""
    settings = Settings.from_env()
    database = Database(settings.database_path)
    database.initialize()
    client = LetterboxdClient(settings)
    service = LetterboxdService(
        client,
        ProfileRepository(database),
        film_repository=FilmRepository(database),
        diary_repository=DiaryEntryRepository(database),
        cache_repository=CacheStateRepository(database),
    )
    mcp = create_mcp(service)
    try:
        mcp.run(transport="stdio", show_banner=False)
    finally:
        client.close()
