# Project Context

## Current milestone

The read-only profile-and-diary MVP is implemented and verified on `feature/mvp-completion`, awaiting commit and pull-request delivery.

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
- Added immutable `Film` and `DiaryEntry` models with nested normalized film data.
- Added strict diary parsing for watched dates, ratings, likes, rewatches, reviews, optional metadata, and the site's real next-page link.
- Added film and diary-entry repositories with stable UPSERTs and joined diary reads.
- Added `LetterboxdService.get_diary` with positive limits, early pagination stopping, loop detection, persistence, and structured 404 translation.
- Added profile and diary freshness decisions backed by persisted cache-state timestamps.
- Added incomplete-diary coverage handling and a `diary_complete` marker for real final pages.
- Added forced live refresh behavior through `refresh=True`.
- Added the local FastMCP stdio runtime with only the read-only `get_profile` and `get_diary` tools.
- Added typed tool-boundary validation and structured Pydantic serialization.

## Files changed

- Updated project metadata, Python version, dependency declarations, and ignore rules.
- Added the package entry points and initial subsystem packages under `src/letterboxd_mcp`.
- Added a minimal package/entry-point test.
- Added `README.md`, this context file, the product specification, and Codex workflow documentation.
- Added `config.py`, `errors.py`, and focused configuration/error tests.
- Added the packaged SQLite schema, database adapter, cache-state repository, and isolated database tests.
- Added `client.py` and deterministic HTTP tests for success, retries, failures, encoding, URL safety, and session lifecycle.
- Added the profile model, parser, repository, service, offline fixtures, and focused tests.
- Added diary and film models, the diary parser, film/diary repositories, and paginated service integration without permanent diary test files.

## Key design decisions

- Python 3.12 is the minimum supported runtime.
- The existing `src/letterboxd_mcp` package is the application root.
- The console and module entry points start the FastMCP stdio runtime.
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
- Fresh profile cache entries are reused for 30 minutes by default; `refresh=True` bypasses freshness.
- Diary rows use viewing IDs as stable identities and expose their associated film as nested structured data.
- Diary pagination follows `.pagination a.next` and stops as soon as the requested limit is collected.
- Sparse diary film data does not overwrite richer cached film years or poster URLs with `None`.
- Fresh diary cache entries are reused for 10 minutes by default when they cover the requested limit or carry a matching completion marker.
- Partial diary refreshes replace the cached snapshot and clear completion state; larger later requests fetch enough public pages again.
- MCP adapters contain validation and registration only; all cache, HTTP, parsing, and persistence work remains in the layers below them.

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
- PR `#5` was merged into `main` at `9ddd8cb` after the user completed the merge.
- Temporary live validation returned and persisted 51 entries across two real diary pages using an automatically discarded SQLite database.
- Temporary offline edge-case validation covered rated, unrated, sparse, liked, rewatch, review, empty, malformed, and repository round-trip behavior; the check file was deleted afterward.
- A focused live selector check confirmed unliked and liked states as `False` and `True`, with ratings normalized to `3.0` and `4.5`.
- `uv build` — passed; diary/film models, repositories, parser, and service are present in the wheel.
- `uv run pytest -q` — passed, 60 tests after updating entry-point coverage for the stdio runtime.
- Disposable temporary-database verification — passed for clean SQLite initialization, profile cache hit/stale/forced refresh, partial and complete diary cache behavior, larger-limit refetching, both in-memory MCP tool calls, typed serialization, and MCP error propagation; the script was removed afterward.

## Current limitations

- Only public Letterboxd profile and diary reads are supported.
- Letterboxd challenge pages are surfaced as errors; the project does not attempt CAPTCHA or anti-bot bypasses.
- The scraper depends on current public page markup and may require parser maintenance when Letterboxd changes it.
- No authentication, private data, write operations, browser automation, or remote hosting is included.

## Next implementation step

Commit and deliver `feature/mvp-completion` through its pull request. Stop before adding post-MVP resources unless the user explicitly requests them.
