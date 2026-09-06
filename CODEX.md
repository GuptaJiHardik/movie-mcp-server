# Project Context

## Current milestone

Phase 1 core infrastructure and Phase 2 profile reads are complete. The next capability is diary reads.

## Completed functionality

- Established a Python 3.12+ `src`-layout package.
- Added the initial runtime and test dependencies.
- Added importable package, module, and console entry points.
- Created package boundaries for database repositories, models, parsers, and MCP tools.
- Added development setup and architecture documentation.
- Added immutable typed runtime settings with documented defaults and optional environment overrides.
- Added the shared structured error hierarchy for user, film, fetch, challenge, parse, and database failures.
- Added idempotent SQLite initialization with all planned MVP and post-MVP tables and indexes.
- Added safe connection and transaction lifecycle handling with commit, rollback, and structured database errors.
- Added cache-state timestamp persistence with stable-identity UPSERT and UTC normalization.
- Added a reusable Letterboxd HTTP client with explicit headers/timeouts and bounded retry behavior.
- Added challenge-page and cross-origin redirect detection without CAPTCHA bypass behavior.
- Added the immutable `Profile` model with optional profile metadata and timezone-aware fetch timestamps.
- Added a page-scoped profile parser for current public profile markup, including normal and sparse fixtures.
- Added profile UPSERT/read persistence and the `LetterboxdService.get_profile` orchestration path.
- Added structured 404-to-`UserNotFoundError` translation and safe username validation.

## Files changed

- Updated project metadata, Python version, dependency declarations, and ignore rules.
- Added the package entry points and initial subsystem packages under `src/letterboxd_mcp`.
- Added a minimal package/entry-point test.
- Added `README.md`, this context file, the product specification, and Codex workflow documentation.
- Added `config.py`, `errors.py`, and focused configuration/error tests.
- Added the packaged SQLite schema, database adapter, cache-state repository, and isolated database tests.
- Added `client.py` and deterministic HTTP tests for success, retries, failures, encoding, URL safety, and session lifecycle.
- Added the profile model, parser, repository, service, offline fixtures, and focused tests.

## Key design decisions

- Python 3.12 is the minimum supported runtime.
- The existing `src/letterboxd_mcp` package is the application root.
- The console entry point remains lightweight until the FastMCP runtime feature is implemented.
- Scraping, persistence, models, and tools have separate package boundaries from the beginning.
- Settings can be constructed from an explicit mapping so tests do not depend on process-global environment state.
- Environment variables use the `LETTERBOXD_MCP_` prefix and invalid numeric or unsafe values fail early.
- Expected operational failures share `LetterboxdError` while retaining machine-readable context attributes.
- Every feature now starts from synchronized `main`, is reviewed in a pull request, and is merged before the next feature begins.
- SQLite connections enable foreign keys and a five-second busy timeout.
- Repository timestamps are stored as ISO 8601 UTC values and exposed as timezone-aware `datetime` objects.
- Resource-specific repositories remain with their profile, diary, and later capability branches.
- HTTP retries cover connection timeouts and transient 429/5xx responses with exponential backoff.
- Numeric `Retry-After` values are honored with a 60-second upper bound.
- The client accepts only the configured origin, closes every response, returns decoded HTML, and performs no parsing.
- Profile selectors remain isolated in the profile parser; SQL remains isolated in the profile repository.
- Missing bio, avatar, and counts remain `None`; a missing profile boundary or display name raises `ParseError`.
- Profile reads currently fetch on every call while accepting `refresh` for forward-compatible API stability; cache freshness remains a separate feature.

## Tests executed

- `uv sync --dev` — passed using CPython 3.12.14.
- `uv run pytest` — passed, 3 tests.
- `uv run letterboxd-mcp` — passed and printed the foundation readiness message.
- `uv run python --version` — confirmed Python 3.12.14.
- `uv run pytest` — passed, 17 tests after configuration and error implementation.
- Direct `Settings.from_env({})` verification — passed with documented defaults.
- `uv run pytest` — passed, 28 tests after SQLite implementation.
- `uv build` — passed; wheel and source distribution were produced.
- Wheel inspection — confirmed `letterboxd_mcp/database/schema.sql` is packaged.
- `uv run pytest` — passed, 44 tests after HTTP client implementation.
- `uv build` — passed with both `client.py` and `database/schema.sql` present in the wheel.
- `uv run pytest tests/test_profile_parser.py tests/database/test_profile_repository.py tests/test_service.py -q` — passed, 14 tests.
- `uv run pytest -q` — passed, 59 tests after profile-read implementation.
- `uv build` — passed; the profile model, parser, repository, and service are present in the wheel.
- One opt-in live parser check against `/dave/` was stopped by the existing challenge detector on an HTTP 200 challenge response; no bypass was attempted and offline acceptance remained green.

## Current limitations

- Diary parsing/persistence, cache freshness, and MCP tools do not exist yet.
- Profile reads always fetch until the dedicated cache/refresh feature is implemented.
- The console command only confirms successful installation.

## Next implementation step

Implement the diary model, parser, pagination, repositories, and service path on `feature/diary-read` from synchronized `main`.
