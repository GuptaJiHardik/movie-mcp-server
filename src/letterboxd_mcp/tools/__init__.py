"""Thin FastMCP tool adapters."""

from letterboxd_mcp.tools.diary_tools import register_diary_tool
from letterboxd_mcp.tools.profile_tools import register_profile_tool

__all__ = ["register_diary_tool", "register_profile_tool"]
