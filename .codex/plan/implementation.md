# Letterboxd MCP Server — MVP Implementation Plan

## Purpose
This document is the durable implementation roadmap for the Letterboxd read-only MCP MVP.

The project uses Python 3.12+, FastMCP 4+, `requests`, BeautifulSoup, Pydantic, and SQLite.
The MVP includes public profile, diary, and enriched watched-film reads exposed through MCP with local SQLite caching.

Do not expand scope unless the MVP is complete and a later requirement explicitly asks for it.

## MVP Scope

Required:
- Public profile read
- Public diary read with pagination
- Enriched public watched-films read with bounded pagination
- SQLite persistence/cache
- Cache freshness and forced refresh
- FastMCP stdio server
- `get_profile`
- `get_diary`
- `get_films`
- Basic offline verification and one opt-in live smoke flow
- README/CODEX project-state documentation

Not required for this MVP:
- Watchlist
- Lists
- Popular films
- Cached movie search
- Login/authenticated scraping
- Playwright
- Write operations
- Remote MCP hosting
- Redis/PostgreSQL
- Background synchronization

Existing database tables or code already completed for future resources must not be removed merely because those features are outside the MVP.

## Status Legend
- `Not started`: no implementation work has begun.
- `In progress`: implementation exists but is not complete/merged.
- `Blocked`: completion depends on a documented issue.
- `Complete`: accepted, tested, documented, and merged.

## Progress Ledger

| Phase | Feature | Status | Branch/Commit | Tests | Notes |
|---|---|---|---|---|---|
| 0 | Project foundation | Complete | PR `#1` / `main` `fff3eb9` | 3 tests passed; CLI passed | Keep unchanged |
| 1 | Configuration and errors | Complete | PR `#2` / `8808140` | 17 tests passed | Keep unchanged |
| 1 | SQLite storage | Complete | PR `#3` / `82eb450` | 28 tests passed; build passed | Keep unchanged |
| 1 | HTTP client | Complete | PR `#4` / `5271f57` | 44 tests passed; build passed | Keep unchanged |
| 2 | Profile read | Complete | PR `#5` / `main` `9ddd8cb` | 59 tests passed; build passed | Keep unchanged |
| 2 | Diary read | Complete | PR `#6` / `main` `2a51164` | Temporary live/offline checks passed; build passed | Merged into `main` by the user |
| 3 | MVP completion | In progress | `feature/mvp-completion` | 60 tests passed; build and disposable MVP check passed | Implementation verified; awaiting commit and pull-request delivery |
| 4 | Enriched watched films | In progress | `feature/mvp-completion` | 72 tests and build passed; live selectors passed | Implementation verified; live tool smoke challenge-blocked; delivery remains |

## Completed Work — Do Not Redesign

### Project Foundation
Already delivered:
- `src` package structure
- Python 3.12+ runtime
- dependencies and CLI entry point
- repository ignores
- README and `CODEX.md`

### Configuration and Errors
Already delivered:
- typed configuration
- database path
- HTTP timeout/User-Agent/retries
- cache TTL configuration
- structured project errors

### SQLite Storage
Already delivered:
- idempotent SQLite initialization
- current schema and indexes
- transaction handling
- UPSERT support
- timestamps/cache-state operations
- database error wrapping

Do not shrink or redesign the completed schema just because some future feature tables are unused by the MVP.

### HTTP Client
Already delivered:
- reusable `requests.Session`
- browser-like User-Agent
- explicit timeouts
- limited retry handling
- UTF-8 handling
- challenge-page detection
- structured fetch failures

### Profile Read
Already delivered:
- `Profile` model/parser
- repository integration
- `LetterboxdService.get_profile`
- sparse/optional value behavior
- unexpected-markup handling

### Diary Read
Current work must be completed without expanding its scope:
- `Film` and `DiaryEntry` models
- diary parser
- URL/date/rating/rewatch normalization
- real next-page pagination
- requested-limit stopping
- film + diary persistence

After diary is accepted, merge PR `#6` before starting the final MVP branch.

## Remaining Work — One Branch Only

### `feature/mvp-completion`

This remains the only final MVP feature branch after diary.

It combines cache behavior, FastMCP runtime, enriched watched films, MVP verification, and documentation.

### A. Cache and Refresh
Implement only the cache behavior needed by profile and diary.

Requirements:
- use stored fetch timestamps
- use `profile` and `diary` cache states for freshness
- use a `diary_complete` cache-state marker when the cached rows reach the real final page
- profile TTL: 30 minutes
- diary TTL: 10 minutes
- return fresh cached data without HTTP
- fetch again when a larger diary limit exceeds incomplete cached coverage
- `refresh=True` forces a live fetch
- successful refresh updates SQLite
- failed refresh surfaces the error
- do not present stale data as fresh

Film metadata TTL may remain configurable if already present, but no standalone film-detail feature is required.

### B. FastMCP Runtime
Create the local stdio FastMCP server.

Expose only:

```python
get_profile(username: str, refresh: bool = False)

get_diary(
    username: str,
    limit: int = 50,
    refresh: bool = False,
)

get_films(
    username: str,
    limit: int = 10,
    offset: int = 0,
    refresh: bool = False,
)
```

Rules:
- tools are read-only
- validate inputs at tool boundary
- delegate all work to the service layer
- no selectors in tool code
- no SQL in tool code
- return typed/serializable structured data

### C. MVP Verification
Keep verification focused.

Required checks:
- clean SQLite startup
- profile service works
- diary service works
- diary pagination works
- positive diary limit is respected
- fresh cache avoids an HTTP request
- `refresh=True` performs a live refresh
- MCP can call `get_profile`
- MCP can call `get_diary`
- MCP can call `get_films`
- structured errors serialize correctly
- one opt-in public live smoke flow succeeds

Use disposable scripts and temporary databases for live checks, then remove them.
Focused permanent parser, repository, service, and MCP tests are required for the newly authorized `get_films` scope.
Do not create a large testing matrix for features outside the three-tool MVP.

### D. Documentation
Update README with:
- install command
- local configuration
- stdio startup
- the three MCP tools
- simple examples
- cache/refresh behavior
- public-read-only limitation

Update `CODEX.md` with:
- completed functionality
- important files
- current architecture
- tests/checks performed
- known limitations
- MVP completion state

### E. Enriched Watched Films
Implement `get_films(username, limit=10, offset=0, refresh=False)` with a
maximum limit of 20 and newest-added ordering.

Requirements:
- fully synchronize the profile's unique watched collection and public diary
- return one film per title with every dated diary viewing nested beneath it
- enrich only the requested window with original title, tagline, synopsis,
  runtime, directors, genres, top-ten cast, and Letterboxd average rating
- include the profile's rating, liked state, and latest public review when present
- use 10-minute collection/review caching and the existing 24-hour film TTL
- force collection, diary, selected film details, and selected review refreshes
  when `refresh=True`
- surface fetch, challenge, parse, and database errors without partial success
- keep community reviews, private data, authentication, and browser automation
  outside the MVP

## Architecture Rule

Preserve this flow:

```text
MCP tool
-> service
-> repository/cache
-> HTTP client when needed
-> BeautifulSoup parser
-> typed model
-> SQLite UPSERT
-> structured result
```

Layer ownership:
- HTTP behavior -> client
- selectors/parsing -> parser
- SQL -> repository/database
- orchestration/cache decisions -> service
- MCP interface -> tools/server

Do not move implementation logic into MCP tool functions.

## Data Rules
- SQLite is a local cache/store, not Letterboxd's source of truth.
- Never return raw HTML.
- Preserve absent optional values as `None`.
- Normalize dates to `YYYY-MM-DD`.
- Normalize ratings to numeric values.
- Normalize film paths to `/film/{slug}/`.
- Do not convert fetch/parse/database failures into empty successful results.

## Simplified Git Workflow

Completed branches and PR history stay unchanged.

For the remaining work:

1. Finish and merge the existing diary PR.
2. Sync local `main` with `origin/main`.
3. Create only `feature/mvp-completion`.
4. Implement cache + MCP runtime + `get_films` + MVP verification + docs in that branch.
5. Make logical commits inside the same branch when useful.
6. Run the focused MVP checks.
7. Update `CODEX.md` and this progress ledger.
8. Push the branch once the combined MVP work is ready.
9. Open one PR into `main`.
10. Merge it after checks pass.
11. Sync local `main`.

Do not create separate branches for cache, MCP runtime, hardening, smoke tests, or documentation.

Do not force-push, commit secrets, commit `server.db`, or include unrelated work.

## MVP Completion Criteria

The project MVP is complete when:
- profile read is complete
- diary read is complete
- `get_profile` works through MCP
- `get_diary` works through MCP
- `get_films` works through MCP
- diary pagination works
- watched-film limit/offset pagination and enrichment work
- SQLite cache is reused
- `refresh=True` forces live refresh
- structured errors are preserved
- focused offline checks pass
- one opt-in live smoke flow succeeds
- README and `CODEX.md` describe the finished MVP

After these conditions pass, stop implementation.
Post-MVP Letterboxd read tools must be planned separately only if explicitly requested.
