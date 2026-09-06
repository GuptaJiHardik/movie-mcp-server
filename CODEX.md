# Project Context

## Current milestone

Phase 1 configuration and structured errors are implemented. The next milestone is SQLite storage.

## Completed functionality

- Established a Python 3.12+ `src`-layout package.
- Added the initial runtime and test dependencies.
- Added importable package, module, and console entry points.
- Created package boundaries for database repositories, models, parsers, and MCP tools.
- Added development setup and architecture documentation.
- Added immutable typed runtime settings with documented defaults and optional environment overrides.
- Added the shared structured error hierarchy for user, film, fetch, challenge, parse, and database failures.

## Files changed

- Updated project metadata, Python version, dependency declarations, and ignore rules.
- Added the package entry points and initial subsystem packages under `src/letterboxd_mcp`.
- Added a minimal package/entry-point test.
- Added `README.md`, this context file, the product specification, and Codex workflow documentation.
- Added `config.py`, `errors.py`, and focused configuration/error tests.

## Key design decisions

- Python 3.12 is the minimum supported runtime.
- The existing `src/letterboxd_mcp` package is the application root.
- The console entry point remains lightweight until the FastMCP runtime feature is implemented.
- Scraping, persistence, models, and tools have separate package boundaries from the beginning.
- Settings can be constructed from an explicit mapping so tests do not depend on process-global environment state.
- Environment variables use the `LETTERBOXD_MCP_` prefix and invalid numeric or unsafe values fail early.
- Expected operational failures share `LetterboxdError` while retaining machine-readable context attributes.
- Every feature now starts from synchronized `main`, is reviewed in a pull request, and is merged before the next feature begins.

## Tests executed

- `uv sync --dev` — passed using CPython 3.12.14.
- `uv run pytest` — passed, 3 tests.
- `uv run letterboxd-mcp` — passed and printed the foundation readiness message.
- `uv run python --version` — confirmed Python 3.12.14.
- `uv run pytest` — passed, 17 tests after configuration and error implementation.
- Direct `Settings.from_env({})` verification — passed with documented defaults.

## Current limitations

- No Letterboxd HTTP client, parsing, persistence, caching, service, or MCP tools exist yet.
- The console command only confirms successful installation.

## Next implementation step

Implement the idempotent SQLite schema and repository infrastructure on `feature/sqlite-storage`.
