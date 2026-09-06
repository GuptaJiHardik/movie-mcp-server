PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS profiles (
    username TEXT PRIMARY KEY COLLATE NOCASE,
    display_name TEXT NOT NULL,
    bio TEXT,
    avatar_url TEXT,
    films_count INTEGER CHECK (films_count IS NULL OR films_count >= 0),
    followers_count INTEGER CHECK (followers_count IS NULL OR followers_count >= 0),
    following_count INTEGER CHECK (following_count IS NULL OR following_count >= 0),
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS films (
    slug TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    year INTEGER,
    url TEXT NOT NULL,
    poster_url TEXT,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS diary_entries (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL COLLATE NOCASE,
    film_slug TEXT NOT NULL,
    watched_date TEXT NOT NULL,
    rating REAL CHECK (rating IS NULL OR (rating >= 0.5 AND rating <= 5.0)),
    rewatch INTEGER NOT NULL DEFAULT 0 CHECK (rewatch IN (0, 1)),
    liked INTEGER CHECK (liked IS NULL OR liked IN (0, 1)),
    review_url TEXT,
    fetched_at TEXT NOT NULL,
    FOREIGN KEY (film_slug) REFERENCES films(slug) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL COLLATE NOCASE,
    film_slug TEXT NOT NULL,
    review_url TEXT NOT NULL,
    reviewed_date TEXT,
    rating REAL CHECK (rating IS NULL OR (rating >= 0.5 AND rating <= 5.0)),
    liked INTEGER CHECK (liked IS NULL OR liked IN (0, 1)),
    review_text TEXT,
    fetched_at TEXT NOT NULL,
    FOREIGN KEY (film_slug) REFERENCES films(slug) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS watchlist (
    username TEXT NOT NULL COLLATE NOCASE,
    film_slug TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (username, film_slug),
    FOREIGN KEY (film_slug) REFERENCES films(slug) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lists (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL COLLATE NOCASE,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    film_count INTEGER CHECK (film_count IS NULL OR film_count >= 0),
    url TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    UNIQUE (username, slug)
);

CREATE TABLE IF NOT EXISTS list_items (
    list_id TEXT NOT NULL,
    film_slug TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    note TEXT,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (list_id, film_slug),
    FOREIGN KEY (list_id) REFERENCES lists(id) ON DELETE CASCADE,
    FOREIGN KEY (film_slug) REFERENCES films(slug) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cache_state (
    resource_type TEXT NOT NULL,
    resource_key TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (resource_type, resource_key)
);

CREATE INDEX IF NOT EXISTS idx_diary_entries_username_watched_date
    ON diary_entries(username, watched_date);
CREATE INDEX IF NOT EXISTS idx_diary_entries_username_film_slug
    ON diary_entries(username, film_slug);
CREATE INDEX IF NOT EXISTS idx_reviews_username
    ON reviews(username);
CREATE INDEX IF NOT EXISTS idx_watchlist_username
    ON watchlist(username);
CREATE INDEX IF NOT EXISTS idx_films_title
    ON films(title);
