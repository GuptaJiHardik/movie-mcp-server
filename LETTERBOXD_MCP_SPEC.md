# Letterboxd Read-Only MCP Server — MVP Spec

## 1. Goal

Build a local-first, read-only MCP server for public Letterboxd data.

Use `requests + BeautifulSoup` for scraping, SQLite (`server.db`) for cache/storage, and FastMCP 4+ for MCP tools.

Current scope:

* public read operations
* profile read
* diary read
* enriched watched-films read
* SQLite caching
* local FastMCP stdio server

Out of scope:

* login/authenticated scraping
* write operations
* Playwright
* private data
* CAPTCHA bypass
* remote MCP hosting
* other post-MVP Letterboxd tools

Do not expand scope unless explicitly requested after MVP completion.

## 2. Validated Findings

Already validated:

* Public profile pages work without authentication.
* Public diary pages work without authentication.
* Profile name/counts can be parsed.
* Diary title, film URL/slug, year, watched date, rating, and rewatch state can be parsed when present.
* Diary pagination works.
* Missing optional values remain `None`.
* HTTP 200 does not guarantee parse success.
* Pagination should follow the actual next-page link.
* `requests + BeautifulSoup` is sufficient for profile, diary, watched-film,
  film-detail, and profile-review reads.

Validated and now included in the current MVP:

* `/{username}/films/by/added/`
* profile-specific public review URLs
* `/film/{slug}/`

Known but not part of the current MVP:

* community review collections
* `/{username}/watchlist/`
* `/{username}/lists/`
* individual list pages
* `/films/popular/`

These must not be implemented during the current MVP.

If added later, each page must first be validated before exposing an MCP tool.

## 3. Stack

* Python 3.12+
* FastMCP 4+
* requests
* beautifulsoup4
* pydantic
* sqlite3
* pytest

Do not add Redis, PostgreSQL, queues, or browser automation for the MVP.

## 4. Architecture

```text
MCP Client
    ->
FastMCP Tool
    ->
LetterboxdService
    ->
SQLite Repository / Cache
    ->
LetterboxdClient when live fetch is needed
    ->
HTML
    ->
BeautifulSoup Parser
    ->
Typed Model
    ->
SQLite UPSERT
    ->
Structured Result
```

MCP tools must remain thin.

They must not contain:

* scraping logic
* BeautifulSoup selectors
* SQL logic
* caching implementation details

SQLite is a local cache/store, not Letterboxd's source of truth.

## 5. Request Flow

1. Validate tool input.
2. Service checks SQLite.
3. Return cached data if fresh.
4. If stale/missing or `refresh=True`, fetch Letterboxd HTML.
5. Detect HTTP/challenge problems.
6. Parse with a page-specific parser.
7. Normalize into a typed model.
8. UPSERT into SQLite.
9. Return structured data.

## 6. MVP MCP Tools

Only expose these tools:

```python
get_profile(
    username: str,
    refresh: bool = False,
)
```

Purpose:

* return public profile information
* use cache when fresh
* perform live fetch when needed

```python
get_diary(
    username: str,
    limit: int = 50,
    refresh: bool = False,
)
```

Purpose:

* return public diary entries
* support pagination
* stop when requested `limit` is reached
* use cache when fresh
* perform live fetch when needed

```python
get_films(
    username: str,
    limit: int = 10,
    offset: int = 0,
    refresh: bool = False,
)
```

Purpose:

* return unique watched titles ordered by newest added
* support `limit`/`offset` pagination with a maximum limit of 20
* nest every public dated diary viewing for each returned title
* include core film metadata, directors, genres, top-ten cast, aggregate rating,
  profile rating/like state, and the profile's latest public review
* fully synchronize public collection and diary snapshots when stale
* enrich only the requested result window

No other MCP tools are required for this MVP.

## 7. Project Structure

```text
letterboxd-mcp/
|-- pyproject.toml
|-- README.md
|-- CODEX.md
|-- LETTERBOXD_MCP_SPEC.md
|-- src/letterboxd_mcp/
|   |-- client.py / config.py / service.py / server.py
|   |-- models/{profile,film,diary,watched}.py
|   |-- parsers/{profile,diary,watched,film_details,review}.py
|   |-- database/{db.py,schema.sql,repositories/}
|   `-- tools/{profile_tools,diary_tools,film_tools}.py
`-- tests/  (existing committed coverage)
```

Important:

Existing completed files, tables, or modules for future functionality must not be deleted merely because they are outside the current MVP.

The structure above describes what the MVP actively requires.

## 8. HTTP Client Requirements

`LetterboxdClient` must:

* reuse `requests.Session`
* use a browser-like User-Agent
* use explicit timeouts
* decode UTF-8 safely when needed
* use limited retries for transient 429/5xx
* never bypass CAPTCHA/challenges
* detect strong challenge-page signals
* raise structured fetch errors
* perform HTTP work only, not parsing

## 9. Parser Requirements

Parsers must:

* accept HTML and return typed models
* never perform network calls
* keep selectors isolated by page
* preserve missing optional values as `None`
* normalize film URLs to canonical `/film/{slug}/`
* normalize dates to `YYYY-MM-DD`
* normalize ratings to numeric values
* use the actual next-page link
* raise parse errors for unexpected markup

Do not return fake empty data when expected markup is missing.

## 10. SQLite

The SQLite schema already implemented must remain unchanged.

Existing tables may include:

* `profiles`
* `films`
* `diary_entries`
* `reviews`
* `watchlist`
* `lists`
* `list_items`
* `cache_state`

Do not remove completed schema elements simply because some are not currently used.

MVP-active tables:

### `profiles`

Important fields:

* username PK
* display_name
* bio
* avatar_url
* films_count
* followers_count
* following_count
* fetched_at

### `films`

Important fields:

* slug PK
* title
* year
* url
* poster_url
* fetched_at

### `diary_entries`

Important fields:

* id PK
* username
* film_slug
* watched_date
* rating
* rewatch
* liked
* review_url
* fetched_at

Use UPSERT where stable identity exists.

## 11. Cache Policy

Cache TTL values must remain configurable.

MVP defaults:

* profile: 30 minutes
* diary: 10 minutes
* watched collection and profile review: 10 minutes
* generic enriched film details: 24 hours

Existing film metadata TTL configuration may remain unchanged if already implemented.

Behavior:

* fresh cache -> return without HTTP request
* stale/missing cache -> live fetch
* `refresh=True` -> bypass freshness check
* successful refresh -> update SQLite
* failed refresh -> surface the live refresh error
* incomplete diary cache -> fetch when it cannot satisfy a larger requested limit
* final diary page reached -> store a `diary_complete` cache-state marker
* `get_films` stale/missing snapshot -> fully synchronize watched collection and diary
* `get_films refresh=True` -> also refresh every film and review in the selected window

Do not present stale data as fresh.

## 12. Models

MVP-active Pydantic models:

* `Profile`
* `Film`
* `DiaryEntry`
* `CastMember`
* `FilmDetails`
* `UserFilm`
* `Viewing`
* `UserReview`
* `WatchedFilm`
* `WatchedFilmsPage`

Return normalized structured data.

Never return raw HTML from MCP tools.

Existing future models already implemented must not be removed.

## 13. Errors

Keep existing structured errors such as:

* `UserNotFoundError`
* `FilmNotFoundError`
* `LetterboxdFetchError`
* `ChallengePageError`
* `ParseError`
* `DatabaseError`

A HTTP 200 response with broken or unrecognized expected markup must not become an empty successful result.

## 14. Testing

Testing should remain focused on MVP behavior.

Existing committed tests and fixtures remain valid.
The newly authorized `get_films` scope requires focused permanent offline parser,
repository, service, and MCP coverage. Live checks use disposable scripts and
temporary databases that are removed after use.

Required coverage:

* normal profile
* sparse profile
* normal diary
* rated diary
* unrated diary
* multi-page diary
* empty diary when available
* malformed/unexpected HTTP-200 markup
* cache hit
* cache miss/stale cache
* forced refresh
* MCP serialization/error behavior
* watched collection pagination and newest-added ordering
* full diary synchronization and nested repeat viewings
* film detail, top-ten cast, aggregate rating, and latest profile review
* `get_films` limit/offset validation, cache reuse, and forced refresh

Keep a small opt-in live smoke flow.

Offline tests must not require internet access.

Do not build large test suites for post-MVP functionality.

## 15. FastMCP

Use FastMCP 4+:

```python
from fastmcp import FastMCP

mcp = FastMCP("Letterboxd MCP")
```

Requirements:

* local `stdio` server
* typed tool inputs
* typed/serializable outputs
* thin tool wrappers
* service-layer delegation
* read-only annotations where supported

Remote MCP hosting is outside MVP scope.

## 16. Implementation Order

Completed work must not be redesigned.

Current implementation order:

1. Project structure/dependencies. `[COMPLETE]`
2. Config and custom errors. `[COMPLETE]`
3. SQLite schema/init. `[COMPLETE]`
4. `LetterboxdClient`. `[COMPLETE]`
5. Profile model/parser/repository/service. `[COMPLETE]`
6. Profile verification/tests. `[COMPLETE]`
7. Diary model/parser/pagination/repositories/service. `[COMPLETE]`
8. Profile/diary cache freshness and FastMCP runtime. `[COMPLETE]`
9. Register and test `get_profile` and `get_diary`. `[COMPLETE]`
10. Add watched collection, film-detail, and profile-review parsers.
11. Add migration-safe persistence and enriched watched-film models.
12. Implement and register `get_films`.
13. Verify all three tools, cache reuse, and forced refresh.
14. Run focused offline checks and one opt-in live smoke flow.
15. Update README and `CODEX.md`.
16. Push, merge, synchronize `main`, and stop implementation.

Do not implement community reviews, watchlist, lists, popular films, or cached search during this MVP.

## 17. Development Rules

* Do not modify completed functionality unless required to integrate the remaining MVP.
* Implement only required MVP behavior.
* Keep client, parser, repository, service, and MCP layers separate.
* Selectors belong only in parsers.
* SQL belongs only in database/repository code.
* HTTP behavior belongs only in the client.
* Cache decisions belong in the service layer.
* Never return raw HTML from MCP tools.
* Never silently ignore parser failures.
* Prefer simple code over premature abstractions.
* Use low concurrency and polite request behavior.
* Do not add features beyond the explicitly authorized three-tool MVP.

## 18. Git Workflow

Completed branches and PR history remain unchanged.

The existing diary feature must be finished and merged using its current branch/PR.

After diary is merged:

1. Sync local `main` with `origin/main`.
2. Create one branch:

```text
feature/mvp-completion
```

3. Use this single branch for:

   * cache/refresh
   * FastMCP runtime
   * MCP tools
   * enriched watched films
   * focused MVP verification
   * README
   * `CODEX.md`

4. Logical commits may be created inside the same branch.

5. Do not create separate branches for each remaining operation.

6. Push the branch after the combined MVP work is ready.

7. Create one final PR.

8. Merge after checks pass.

9. Sync local `main`.

10. Stop implementation.

Do not create separate branches such as:

```text
feature/cache-refresh
feature/mcp-runtime
feature/mvp-hardening
feature/documentation
feature/live-smoke-tests
```

## 19. CODEX.md Rule

After meaningful tested milestones, update `CODEX.md` with:

* completed functionality
* files changed
* important design decisions
* tests/checks executed
* current limitations
* next implementation step

Do not update `CODEX.md` for every tiny internal change.

At final MVP completion, clearly record that the project should stop before post-MVP features.

## 20. MVP Done Criteria

MVP is complete when:

* profile read is complete
* diary read is complete
* diary pagination works
* `get_profile` works through MCP
* `get_diary` works through MCP
* `get_films` works through MCP
* repeated calls reuse SQLite cache
* `refresh=True` performs a live refresh
* data is typed and normalized
* watched films paginate by limit/offset and include the agreed enrichment
* focused offline verification passes
* one opt-in live smoke flow succeeds
* structured errors are preserved
* README is updated
* `CODEX.md` reflects final MVP state
* no login or browser automation is required

Once these criteria pass:

**STOP IMPLEMENTATION.**

Post-MVP Letterboxd read tools must only be planned or implemented if explicitly requested later.
