# Project Context

## Current milestone

Phase 0 project foundation is complete. The next milestone is Phase 1 configuration and errors.

## Completed functionality

- Established a Python 3.12+ `src`-layout package.
- Added the initial runtime and test dependencies.
- Added importable package, module, and console entry points.
- Created package boundaries for database repositories, models, parsers, and MCP tools.
- Added development setup and architecture documentation.

## Files changed

- Updated project metadata, Python version, dependency declarations, and ignore rules.
- Added the package entry points and initial subsystem packages under `src/letterboxd_mcp`.
- Added a minimal package/entry-point test.
- Added `README.md`, this context file, the product specification, and Codex workflow documentation.

## Key design decisions

- Python 3.12 is the minimum supported runtime.
- The existing `src/letterboxd_mcp` package is the application root.
- The console entry point remains lightweight until the FastMCP runtime feature is implemented.
- Scraping, persistence, models, and tools have separate package boundaries from the beginning.

## Tests executed

- `uv sync --dev` — passed using CPython 3.12.14.
- `uv run pytest` — passed, 3 tests.
- `uv run letterboxd-mcp` — passed and printed the foundation readiness message.
- `uv run python --version` — confirmed Python 3.12.14.

## Current limitations

- No Letterboxd HTTP client, parsing, persistence, caching, service, or MCP tools exist yet.
- The console command only confirms successful installation.

## Next implementation step

Implement typed configuration and the custom error hierarchy on `feature/config-errors`.
