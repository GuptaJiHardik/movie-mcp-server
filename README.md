# Letterboxd MCP

A local-first, read-only MCP server for public Letterboxd profile, diary, and watched-film data. It uses FastMCP over stdio, fetches public pages with `requests`, parses them with BeautifulSoup, and keeps a local SQLite cache.

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

The server exposes exactly three read-only tools:

- `get_profile(username: str, refresh: bool = false)` returns normalized public profile details.
- `get_diary(username: str, limit: int = 50, refresh: bool = false)` returns up to `limit` normalized diary entries, newest first.
- `get_films(username: str, limit: int = 10, offset: int = 0, refresh: bool = false)` returns a page of unique watched titles ordered by newest added and enriched with directors, genres, top-ten cast, runtime, synopsis, aggregate rating, nested diary viewings, and the profile's latest public review.

Example tool arguments:

```json
{"username": "dave"}
```

```json
{"username": "dave", "limit": 25, "refresh": true}
```

```json
{"username": "dave", "limit": 10, "offset": 20}
```

Usernames may contain letters, numbers, underscores, and hyphens. Diary limits must be positive. Watched-film limits must be between 1 and 20, and offsets must be non-negative.

## Cache and configuration

By default, data is stored in `server.db` in the server's working directory. Profiles remain fresh for 30 minutes, profile collections/reviews for 10 minutes, and generic film details for 24 hours. Fresh cached data is returned without an HTTP request; `refresh: true` always requests current public data. `get_films` fully synchronizes the public watched collection and diary when stale, but only enriches its requested 10–20 title window.

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

This MVP only reads public profile, diary, watched-film, film-detail, and profile-review pages. It does not return community reviews, log in, access private data, write to Letterboxd, bypass challenge pages or CAPTCHAs, or use browser automation. Large profiles can require many public page requests during the first full collection/diary synchronization. Letterboxd markup changes or anti-bot challenges can surface as structured fetch or parse errors.

See `LETTERBOXD_MCP_SPEC.md` for the product specification and `.codex/plan/implementation.md` for the implementation ledger.
