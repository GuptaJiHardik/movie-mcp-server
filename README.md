# Letterboxd MCP

A local-first, read-only MCP server for public Letterboxd profile and diary data. It uses FastMCP over stdio, fetches public pages with `requests`, parses them with BeautifulSoup, and keeps a local SQLite cache.

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)

## Install and run

Install the project and its development dependencies:

```shell
uv sync --dev
```

Start the stdio MCP server from the repository root:

```shell
uv run letterboxd-mcp
```

An MCP client should launch that command as a stdio server. For example, from outside the repository, configure the equivalent of:

```json
{
  "mcpServers": {
    "letterboxd": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/letterboxd_mcp",
        "run",
        "letterboxd-mcp"
      ]
    }
  }
}
```

Replace the example path with this repository's absolute path.

## Tools

The server exposes exactly two read-only tools:

- `get_profile(username: str, refresh: bool = false)` returns normalized public profile details.
- `get_diary(username: str, limit: int = 50, refresh: bool = false)` returns up to `limit` normalized diary entries, newest first.

Example tool arguments:

```json
{"username": "dave"}
```

```json
{"username": "dave", "limit": 25, "refresh": true}
```

Usernames may contain letters, numbers, underscores, and hyphens. Diary limits must be positive.

## Cache and configuration

By default, data is stored in `server.db` in the server's working directory. Profiles remain fresh for 30 minutes and diaries for 10 minutes. Fresh cached data is returned without an HTTP request; `refresh: true` always requests current public data. A larger diary request fetches again when the existing cached snapshot is incomplete.

Configuration is optional and uses `LETTERBOXD_MCP_` environment variables. The most useful settings are:

- `LETTERBOXD_MCP_DATABASE_PATH`
- `LETTERBOXD_MCP_PROFILE_TTL_SECONDS`
- `LETTERBOXD_MCP_DIARY_TTL_SECONDS`
- `LETTERBOXD_MCP_CONNECT_TIMEOUT_SECONDS`
- `LETTERBOXD_MCP_READ_TIMEOUT_SECONDS`
- `LETTERBOXD_MCP_MAX_RETRIES`
- `LETTERBOXD_MCP_USER_AGENT`

All TTL and timeout values must be positive. `MAX_RETRIES` may be zero.

## Development

Run the offline test suite and build the distributions:

```shell
uv run pytest
uv build
```

The implementation keeps MCP tools, service/cache decisions, HTTP behavior, parsers, models, and SQLite repositories in separate layers.

## Limitations

This MVP only reads public profile and diary pages. It does not log in, access private data, write to Letterboxd, bypass challenge pages or CAPTCHAs, or use browser automation. Letterboxd markup changes or anti-bot challenges can surface as structured fetch or parse errors.

See `LETTERBOXD_MCP_SPEC.md` for the product specification and `.codex/plan/implementation.md` for the implementation ledger.
