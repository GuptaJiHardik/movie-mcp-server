# Letterboxd MCP

A local-first, read-only MCP server for public Letterboxd data.

The project is under active development. Its MVP will expose public Letterboxd profile and diary data through a local FastMCP stdio server, backed by an SQLite cache. It will not log in to Letterboxd, access private data, modify Letterboxd state, bypass challenge pages, or require browser automation.

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)

## Development setup

Install the project and development dependencies:

```shell
uv sync --dev
```

Run the test suite:

```shell
uv run pytest
```

Verify the package entry point:

```shell
uv run letterboxd-mcp
```

The entry point currently reports that the project foundation is ready. The FastMCP stdio runtime and tools will be added in later implementation phases.

## Planned architecture

```text
MCP client -> FastMCP tool -> service -> SQLite repository/cache
                                      -> HTTP client -> parser -> typed model
```

- MCP tools remain thin and contain no scraping or SQL.
- HTTP behavior is isolated in the Letterboxd client.
- CSS selectors are isolated in page-specific parsers.
- SQL is isolated in database and repository modules.
- Normal tests run offline with saved HTML fixtures.

See `LETTERBOXD_MCP_SPEC.md` for the product specification and `.codex/plan/implementation.md` for the implementation roadmap and progress ledger.
