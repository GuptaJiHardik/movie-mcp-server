# Letterboxd MCP Server Implementation Plan

## Purpose

This document is the durable implementation roadmap and progress record for the Letterboxd MCP server. Update it after every completed feature so a future session can determine what is finished, what was verified, and what comes next.

The project will deliver the complete read-only roadmap using Python 3.12+, FastMCP 4+, `requests`, BeautifulSoup, Pydantic, and SQLite. Each feature starts from synchronized `main` and is delivered through a `feature/<short-name>` branch and pull request. Every completed feature must also update `CODEX.md`, pass its required checks, be committed, pushed, and merged according to `.codex/skills/github_skill.md`.

## Status Legend

- `Not started`: no implementation work has begun.
- `In progress`: implementation exists locally but the feature is not complete or pushed.
- `Blocked`: completion depends on a documented external issue or decision.
- `Complete`: acceptance checks passed, documentation was updated, and the pull request was merged into `main`.

## Progress Ledger

Update the Status, Branch/Commit, Tests, and Notes columns when each feature changes state.

| Phase | Feature | Status | Branch/Commit | Tests | Notes |
|---|---|---|---|---|---|
| 0 | Project foundation | Complete | PR `#1` / `main` `fff3eb9` | 3 tests passed; CLI passed | Merged into `main` after history reconciliation |
| 1 | Configuration and errors | Complete | PR `#2` / `8808140` | 17 tests passed | Delivered through feature PR |
| 1 | SQLite storage | Complete | PR `#3` / `82eb450` | 28 tests passed; build passed | Delivered through feature PR |
| 1 | HTTP client | Complete | PR `#4` / `5271f57` | 44 tests passed; build passed | Delivered through feature PR; Phase 1 complete |
| 2 | Profile read | Complete | PR `#5` / `main` `9ddd8cb` | 59 tests passed; build passed | Merged into `main` by the user |
| 2 | Diary read | In progress | PR `#6` / `14ffa01` | Temporary live/offline checks passed; build passed | Pushed without permanent test files per user request; awaiting merge |
| 2 | Cache and refresh | Not started | `feature/cache-refresh` | Pending | |
| 2 | MCP runtime | Not started | `feature/mcp-runtime` | Pending | |
| 2 | MVP hardening | Not started | `feature/mvp-hardening` | Pending | |
| 3 | User films | Not started | `feature/user-films` | Pending | Requires live page validation |
| 3 | User reviews | Not started | `feature/user-reviews` | Pending | Requires live page validation |
| 3 | User watchlist | Not started | `feature/user-watchlist` | Pending | Requires live page validation |
| 3 | User lists | Not started | `feature/user-lists` | Pending | Requires live page validation |
| 3 | Film details | Not started | `feature/film-details` | Pending | Requires live page validation |
| 3 | Popular films | Not started | `feature/popular-films` | Pending | Requires live page validation |
| 4 | Cached movie search | Not started | `feature/cached-movie-search` | Pending | |
| 4 | Release readiness | Not started | `feature/release-readiness` | Pending | |

## Implementation Phases

### Phase 0: Project Foundation

#### `feature/project-foundation`

- Convert the generated stub into the documented `src` package structure.
- Change the supported runtime to Python 3.12+.
- Add the runtime and test dependencies.
- Configure the console entry point.
- Ignore `server.db`, secrets, caches, build output, and local environments.
- Create the initial README and `CODEX.md` project context.

Completion requires a clean installation and a passing minimal package/entry-point test.

### Phase 1: Core Infrastructure

#### `feature/config-errors`

- Add typed configuration for the database path, HTTP timeout, user agent, retry limits, and cache TTLs.
- Define `UserNotFoundError`, `FilmNotFoundError`, `LetterboxdFetchError`, `ChallengePageError`, `ParseError`, and `DatabaseError`.
- Keep configuration usable from tests without depending on global machine state.

#### `feature/sqlite-storage`

- Add idempotent SQLite initialization and the `profiles`, `films`, `diary_entries`, `reviews`, `watchlist`, `lists`, `list_items`, and `cache_state` tables.
- Add the specified diary, review, watchlist, and film-title indexes.
- Implement transaction handling, stable-identity UPSERTs, timestamps, and cache-state operations.
- Wrap database failures in `DatabaseError` without hiding the original cause.

Completion requires repository tests against isolated temporary databases.

#### `feature/http-client`

- Implement `LetterboxdClient` around one reusable `requests.Session`.
- Send a browser-like user agent and explicit timeouts.
- Retry transient 429 and 5xx responses with limited backoff.
- Decode UTF-8 safely where required.
- Detect strong challenge-page signals and never attempt CAPTCHA bypass.
- Raise structured fetch errors and perform no parsing.

### Phase 2: MVP Capabilities

#### `feature/profile-read`

- Add the `Profile` model and page-specific profile parser.
- Add normal and sparse saved HTML fixtures.
- Add profile repository integration and `LetterboxdService.get_profile`.
- Preserve missing optional values as `None`.
- Treat unexpected HTTP-200 markup as `ParseError`, not an empty success.

#### `feature/diary-read`

- Add `Film` and `DiaryEntry` models and the diary parser.
- Normalize film URLs, dates, ratings, rewatch state, and other optional values.
- Follow the page's real next-page link and stop once the requested limit is collected.
- Persist films and diary entries through repositories.
- Cover rated, unrated, rewatch, empty, malformed, and multi-page fixtures.

#### `feature/cache-refresh`

- Implement freshness checks using stored fetch timestamps.
- Use default TTLs of 30 minutes for profiles, 10 minutes for diaries, and 24 hours for film metadata.
- Return fresh cached data without an HTTP request.
- Make `refresh=True` bypass freshness and replace cached data after a successful fetch.
- Preserve usable cached data if a refresh fails; surface the refresh error rather than presenting stale data as fresh.

#### `feature/mcp-runtime`

- Create a local stdio FastMCP server.
- Register thin, read-only `get_profile` and `get_diary` tools.
- Validate inputs at the tool boundary and delegate all behavior to the service.
- Keep selectors and SQL out of MCP tool functions.
- Add MCP-level serialization and structured-error integration tests.

#### `feature/mvp-hardening`

- Add explicitly opt-in live smoke tests.
- Verify at least one public profile and one diary flow, including pagination where available.
- Verify clean-database startup, cache reuse, and forced refresh through MCP.
- Document installation, configuration, stdio startup, tool examples, limitations, and smoke-test usage.

MVP is complete only when `get_profile` and `get_diary` work through MCP, pagination and caching are verified, `refresh=True` performs a live refresh, data is typed and normalized, fixture tests pass, structured errors are used, and at least one live smoke test succeeds.

### Phase 3: Validated Public Read Tools

Every feature in this phase must begin by validating its public Letterboxd page. Capture representative offline fixtures only after identifying reliable page structure. If validation cannot establish reliable selectors or encounters challenge protection, do not expose or push an incomplete MCP tool; mark the feature blocked and record the evidence.

#### `feature/user-films`

Validate `/{username}/films/`, then add its parser, normalized models, repository/service integration, caching, pagination, tests, and `get_films`.

#### `feature/user-reviews`

Validate `/{username}/reviews/`, then add normalized review parsing, persistence, caching, pagination, tests, and `get_reviews`.

#### `feature/user-watchlist`

Validate `/{username}/watchlist/`, then add watchlist parsing, ordered persistence, caching, pagination, tests, and `get_watchlist`.

#### `feature/user-lists`

Validate the list index and individual list pages, then add list and list-item models, parsers, repositories, caching, pagination, tests, `get_lists`, and `get_list`.

#### `feature/film-details`

Validate `/film/{slug}/`, then add film-detail parsing, canonical identity, 24-hour caching, not-found behavior, tests, and `get_film`.

#### `feature/popular-films`

Validate `/films/popular/`, then add pagination, normalized film results, caching, tests, and `get_popular_films`.

Use 10-minute TTLs for account collections and individual lists, and a 30-minute TTL for popular films.

### Phase 4: Local Search and Release Readiness

#### `feature/cached-movie-search`

- Add `search_cached_movies(query: str, limit: int = 20)`.
- Search cached film titles case-insensitively without performing network requests.
- Rank exact matches first, prefix matches second, and substring matches last.
- Return normalized `Film` results.

#### `feature/release-readiness`

- Run the complete offline suite and the opt-in live smoke suite.
- Verify initialization and MCP startup from a clean local database.
- Audit that every MCP operation is read-only and public-data-only.
- Confirm no login, browser automation, CAPTCHA bypass, or remote hosting was introduced.
- Finalize README and `CODEX.md` with supported tools and known markup limitations.

## Public Interfaces

All network-backed tools accept `refresh: bool = False`. Collection limits must be positive, default to 50, and stop pagination as soon as enough results have been collected.

```python
get_profile(username: str, refresh: bool = False)
get_diary(username: str, limit: int = 50, refresh: bool = False)
get_films(username: str, limit: int = 50, refresh: bool = False)
get_reviews(username: str, limit: int = 50, refresh: bool = False)
get_watchlist(username: str, limit: int = 50, refresh: bool = False)
get_lists(username: str, limit: int = 50, refresh: bool = False)
get_list(username: str, list_slug: str, limit: int = 50, refresh: bool = False)
get_film(film_slug: str, refresh: bool = False)
get_popular_films(limit: int = 50, refresh: bool = False)
search_cached_movies(query: str, limit: int = 20)
```

## Architecture and Data Rules

- Preserve the flow: MCP tool -> service -> repository/cache -> HTTP client -> page parser -> Pydantic model -> UPSERT.
- SQLite is a local cache and store, never the authoritative source.
- Selectors belong only in parsers, SQL only in repositories, and HTTP behavior only in the client.
- Never return or persist raw HTML as tool output.
- Normalize film paths to `/film/{slug}/`, dates to `YYYY-MM-DD`, and ratings to numeric values.
- Preserve absent optional values as `None`.
- Do not silently convert fetch, challenge, parsing, or database failures into empty results.

## Testing Strategy

- Ordinary tests must be offline and use saved HTML fixtures, mocked HTTP responses, temporary SQLite databases, and a controllable clock for TTL behavior.
- Cover success, sparse data, empty data, pagination, malformed HTTP-200 pages, not-found pages, challenge pages, timeouts, retries, database errors, stale cache, fresh cache, and forced refresh.
- Verify MCP return serialization and error behavior without duplicating service logic in the tools.
- Mark live tests separately and require explicit opt-in. Use low request volume and public test pages only.
- Before every feature push, run the feature's focused tests and the complete offline suite.

## Git and Documentation Workflow

Each feature begins only after fetching the remote and fast-forwarding local `main` to `origin/main`. Create its branch from that synchronized base, then complete the feature through a pull request before starting the next feature.

For every feature:

1. Verify `origin`, fetch it, switch to local `main`, and run `git pull --ff-only origin main` with a clean worktree.
2. Create and switch to the planned `feature/<short-name>` branch from `origin/main`.
3. Implement only that feature and its tests.
4. Run focused checks and the complete offline suite.
5. Update `CODEX.md` with completed behavior, files changed, design decisions, tests and results, current limitations, and the next feature.
6. Update the Progress Ledger in this file.
7. Review status and diff, then commit only relevant files with a concise imperative message.
8. Fetch again, incorporate any new `origin/main` commits, and rerun tests before pushing.
9. Push using `git push -u origin feature/<short-name>`.
10. Create a pull request into `main`, verify mergeability and required checks, and squash-merge it without bypassing protections.
11. Fetch and fast-forward local `main` to the merged `origin/main`.
12. Record the commit, tests, pull request, merge result, and updated `main` revision in the Progress Ledger.

Never commit secrets, local databases, caches, or unrelated user work. Never force-push. If authentication, remote conflicts, failing tests, or branch protection prevents completion, preserve the local work, mark the feature blocked, and record the exact blocker.

## Agreed Assumptions

- The roadmap covers the MVP, all post-MVP public read tools, cached search, and release hardening.
- Python 3.12 is the minimum supported version even though the generated stub initially specified 3.14.
- Each feature is merged into `main` before the next feature branch is created.
- The server remains local, stdio-based, unauthenticated, and strictly read-only.
- Exact optional fields for previously unvalidated pages will be finalized from live page evidence while preserving the common normalization and error rules.
