# Letterboxd Read-Only MCP Server — Spec
## 1. Goal
Build a local-first, read-only MCP server for public Letterboxd data.
Use `requests + BeautifulSoup` for scraping, SQLite (`server.db`) for cache/storage, and FastMCP 4+ for MCP tools.
Scope: public read operations only.
Out of scope: login, writes, Playwright, private data, CAPTCHA bypass, remote hosting.

## 2. Validated Findings
Already validated:
- Public profile pages work without authentication.
- Public diary pages work without authentication.
- Profile name/counts can be parsed.
- Diary title, film URL/slug, year, watched date, rating, and rewatch state can be parsed when present.
- Diary pagination works.
- Missing optional values remain `None`.
- HTTP 200 does not guarantee parse success.
- Pagination should follow the actual next-page link.
- `requests + BeautifulSoup` is sufficient for current profile/diary reads.
Not yet validated: `/{username}/films/`, `/{username}/reviews/`, `/{username}/watchlist/`, `/{username}/lists/`, individual lists, `/film/{slug}/`, `/films/popular/`.
Rule: validate an untested page before its MCP tool is considered complete.

## 3. Stack
Python 3.12+, FastMCP 4+, requests, beautifulsoup4, pydantic, sqlite3, pytest.
Do not add Redis, PostgreSQL, queues, or browser automation for the MVP.

## 4. Architecture
```text
MCP Client -> FastMCP Tool -> LetterboxdService
                              -> SQLite Repository
                              -> LetterboxdClient -> HTML -> Parser -> Typed Model -> UPSERT
```
MCP tools must stay thin and contain no scraping or SQL logic.
SQLite is a local cache/store, not the source of truth.

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

## 6. MCP Tools
Phase 1:
- `get_profile(username: str, refresh: bool = False)`
- `get_diary(username: str, limit: int = 50, refresh: bool = False)`
Phase 2 after validation:
- `get_films(username, limit=...)`
- `get_reviews(username, limit=...)`
- `get_watchlist(username, limit=...)`
- `get_lists(username, limit=...)`
- `get_list(username, list_slug, limit=...)`
- `get_film(film_slug)`
- `get_popular_films(limit=...)`
Later local-only tool: `search_cached_movies(...)`.

## 7. Project Structure
```text
letterboxd-mcp/
├── server.py / config.py / requirements.txt / README.md / CODEX.md / server.db
├── letterboxd/
│   ├── client.py / service.py
│   ├── models/{profile,diary,film,review,list}.py
│   └── parsers/{profile,diary,films,reviews,watchlist,lists,film}.py
├── database/
│   ├── db.py / schema.sql
│   └── repositories/
├── tools/{profile_tools,diary_tools,film_tools,list_tools}.py
└── tests/fixtures + parser/service/repository tests
```

## 8. HTTP Client Requirements
`LetterboxdClient` must:
- reuse `requests.Session`
- use a browser-like User-Agent
- use explicit timeouts
- decode UTF-8 safely when needed
- use limited retries for transient 429/5xx
- never bypass CAPTCHA/challenges
- detect strong challenge-page signals
- raise structured fetch errors
- perform HTTP work only, not parsing

## 9. Parser Requirements
Parsers must:
- accept HTML and return typed models
- never perform network calls
- keep selectors isolated by page
- preserve missing optional values as `None`
- normalize film URLs to canonical `/film/{slug}/`
- normalize dates to `YYYY-MM-DD`
- normalize ratings to numeric values
- use real next-page links
- raise parse errors for unexpected markup

## 10. SQLite
Initial tables: `profiles`, `films`, `diary_entries`, `reviews`, `watchlist`, `lists`, `list_items`, `cache_state`.
`profiles`: username PK, display_name, bio, avatar_url, films_count, followers_count, following_count, fetched_at.
`films`: slug PK, title, year, url, poster_url, fetched_at.
`diary_entries`: id PK, username, film_slug, watched_date, rating, rewatch, liked, review_url, fetched_at.
Recommended indexes:
- `diary_entries(username, watched_date)`
- `diary_entries(username, film_slug)`
- `reviews(username)`
- `watchlist(username)`
- `films(title)`
Use UPSERT where stable resource identity exists.

## 11. Cache Policy
Configurable TTL defaults:
- profile: 30 minutes
- diary: 10 minutes
- film metadata: 24 hours
`refresh=True` bypasses freshness checks and forces a live fetch.

## 12. Models
Prefer Pydantic models: `Profile`, `Film`, `DiaryEntry`, `Review`, `LetterboxdList`.
Return normalized structured data, never raw HTML.

## 13. Errors
Define `UserNotFoundError`, `FilmNotFoundError`, `LetterboxdFetchError`, `ChallengePageError`, `ParseError`, `DatabaseError`.
A 200 page with broken/unrecognized expected markup must not become an empty success.

## 14. Testing
Offline tests use saved HTML fixtures.
Cover: normal profile, sparse profile, normal diary, rated diary, unrated diary, multi-page diary, and empty diary when available.
Keep a small opt-in live smoke suite to detect Letterboxd markup changes.
Normal unit tests must not require internet access.

## 15. FastMCP
```python
from fastmcp import FastMCP
mcp = FastMCP("Letterboxd MCP")
```
Use typed inputs/returns and thin service wrappers.
Mark tools read-only where supported.
Start with local `stdio`; remote MCP is outside MVP scope.

## 16. Implementation Order
1. Create structure/dependencies.
2. Add config and custom errors.
3. Add SQLite schema/init.
4. Build `LetterboxdClient`.
5. Build profile model/parser/repository/service.
6. Add profile fixture tests.
7. Build diary model/parser/pagination/repositories/service.
8. Add diary fixture tests.
9. Add cache freshness and `refresh`.
10. Create FastMCP server.
11. Register `get_profile` and `get_diary`.
12. Test through MCP and verify cache reuse.
13. Validate `/films/`, then add `get_films`.
14. Validate `/reviews/`, then add `get_reviews`.
15. Validate watchlist, then add `get_watchlist`.
16. Validate lists, then add list tools.
17. Validate film detail/popular pages, then add those tools.
18. Add useful SQLite-only search tools.

## 17. Development Rules
- Implement one capability at a time.
- Validate a page before exposing its MCP tool.
- Keep client, parser, repository, service, and MCP layers separate.
- Selectors belong only in parsers.
- SQL belongs only in database/repository code.
- Never return raw HTML from MCP tools.
- Never silently ignore parser failures.
- Prefer simple code over premature abstractions.
- Use low concurrency and polite request behavior.

## 18. CODEX.md Rule
After each tested milestone, update `CODEX.md` with:
- completed functionality
- files changed
- key design decisions
- tests executed/results
- current limitations
- next implementation step
This lets a new Codex session recover project state quickly.

## 19. MVP Done Criteria
MVP is complete when:
- `get_profile` works through MCP
- `get_diary` works through MCP
- diary pagination works
- repeated calls use SQLite cache
- `refresh=True` performs live refresh
- data is typed and normalized
- parser fixture tests pass
- at least one live smoke test succeeds
- errors are structured
- no login or browser automation is required
After MVP, validate and add remaining read tools incrementally.
