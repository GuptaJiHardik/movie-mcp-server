"""FastMCP registration for public profile reads."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import StringConstraints

from letterboxd_mcp.models import Profile
from letterboxd_mcp.service import LetterboxdService


Username = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_-]*$"),
]
READ_ONLY_TOOL = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}


def register_profile_tool(mcp: FastMCP, service: LetterboxdService) -> None:
    """Register the read-only profile tool on an MCP server."""

    @mcp.tool(annotations=READ_ONLY_TOOL)
    def get_profile(username: Username, refresh: bool = False) -> Profile:
        """Return normalized public profile information for a Letterboxd user."""
        return service.get_profile(username, refresh=refresh)
