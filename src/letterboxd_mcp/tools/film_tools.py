"""FastMCP registration for enriched public watched-film reads."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from letterboxd_mcp.models import WatchedFilmsPage
from letterboxd_mcp.service import LetterboxdService
from letterboxd_mcp.tools.profile_tools import READ_ONLY_TOOL, Username


FilmLimit = Annotated[int, Field(ge=1, le=20)]
FilmOffset = Annotated[int, Field(ge=0)]


def register_film_tool(mcp: FastMCP, service: LetterboxdService) -> None:
    """Register the enriched watched-films tool on an MCP server."""

    @mcp.tool(annotations=READ_ONLY_TOOL)
    def get_films(
        username: Username,
        limit: FilmLimit = 10,
        offset: FilmOffset = 0,
        refresh: bool = False,
    ) -> WatchedFilmsPage:
        """Return enriched public films watched by a Letterboxd user."""
        return service.get_films(
            username,
            limit=limit,
            offset=offset,
            refresh=refresh,
        )
