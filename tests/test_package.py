from __future__ import annotations

import asyncio
import subprocess
import sys
from unittest.mock import Mock, patch

import letterboxd_mcp
from letterboxd_mcp.server import create_mcp, main


def test_package_metadata() -> None:
    assert letterboxd_mcp.__version__ == "0.1.0"
    assert letterboxd_mcp.main is main


def test_console_main() -> None:
    client = Mock()
    mcp = Mock()

    with (
        patch("letterboxd_mcp.server.Database") as database_type,
        patch("letterboxd_mcp.server.LetterboxdClient", return_value=client),
        patch("letterboxd_mcp.server.create_mcp", return_value=mcp),
    ):
        main()

    database_type.return_value.initialize.assert_called_once_with()
    mcp.run.assert_called_once_with(transport="stdio", show_banner=False)
    client.close.assert_called_once_with()


def test_mcp_registers_only_mvp_tools() -> None:
    mcp = create_mcp(Mock())

    tools = asyncio.run(mcp.list_tools())

    assert {tool.name for tool in tools} == {"get_profile", "get_diary"}


def test_module_entry_point() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "letterboxd_mcp"],
        check=True,
        capture_output=True,
        input="",
        text=True,
    )

    assert result.stdout == ""
