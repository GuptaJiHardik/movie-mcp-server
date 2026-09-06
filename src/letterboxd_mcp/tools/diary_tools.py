"""FastMCP registration for public diary reads."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from letterboxd_mcp.models import DiaryEntry
from letterboxd_mcp.service import LetterboxdService
from letterboxd_mcp.tools.profile_tools import READ_ONLY_TOOL, Username


PositiveLimit = Annotated[int, Field(gt=0)]


def register_diary_tool(mcp: FastMCP, service: LetterboxdService) -> None:
    """Register the read-only diary tool on an MCP server."""

    @mcp.tool(annotations=READ_ONLY_TOOL)
    def get_diary(
        username: Username,
        limit: PositiveLimit = 50,
        refresh: bool = False,
    ) -> list[DiaryEntry]:
        """Return normalized public diary entries for a Letterboxd user."""
        return service.get_diary(username, limit=limit, refresh=refresh)
