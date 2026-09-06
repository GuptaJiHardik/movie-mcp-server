from __future__ import annotations

import subprocess
import sys

import letterboxd_mcp
from letterboxd_mcp.server import main


def test_package_metadata() -> None:
    assert letterboxd_mcp.__version__ == "0.1.0"
    assert letterboxd_mcp.main is main


def test_console_main(capsys) -> None:
    main()

    assert capsys.readouterr().out == "Letterboxd MCP project foundation is ready.\n"


def test_module_entry_point() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "letterboxd_mcp"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == "Letterboxd MCP project foundation is ready.\n"
