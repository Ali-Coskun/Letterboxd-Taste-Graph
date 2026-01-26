-- ============================================================
-- Core user tables
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    display_name TEXT,
    reviews_written INTEGER NOT NULL DEFAULT 0,
    last_fetched_at TIMESTAMP
);

-- ============================================================
-- Core film table (global metadata + “nice-to-haves”)
-- ============================================================

CREATE TABLE IF NOT EXISTS films (
    movie_id TEXT PRIMARY KEY,     -- Your canonical film id (e.g., Letterboxd slug)
    film_name TEXT,
    release_year INTEGER,
    release_date DATE,
    runtime_minutes INTEGER,

    original_language TEXT,
    overview TEXT,

    poster_path TEXT,
    backdrop_path TEXT,

    tmdb_id INTEGER UNIQUE,
    tmdb_type TEXT,                -- "movie" or "tv"
    imdb_id TEXT,

    tmdb_vote_average REAL,
    tmdb_vote_count INTEGER
);

-- ============================================================
-- User ↔ film facts (per-user interactions)
-- ============================================================

CREATE TABLE IF NOT EXISTS user_films (
    username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    movie_id TEXT NOT NULL REFERENCES films(movie_id) ON DELETE CASCADE,

    watched BOOLEAN NOT NULL,
    in_watchlist BOOLEAN NOT NULL,
    rating_val REAL,
    liked BOOLEAN NOT NULL,
    has_review BOOLEAN NOT NULL,

    PRIMARY KEY (username, movie_id)
);

-- ============================================================
-- Review-like counts (aggregated)
--   "liker_username liked_count reviews written by author_username"
-- ============================================================

CREATE TABLE IF NOT EXISTS liked_review_counts (
    liker_username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    author_username TEXT NOT NULL,
    liked_count INTEGER NOT NULL,
    PRIMARY KEY (liker_username, author_username)
);

-- ============================================================
-- Lookup tables (normalized metadata)
-- ============================================================

CREATE TABLE IF NOT EXISTS genres (
    genre_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS keywords (
    keyword_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS people (
    person_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

-- ============================================================
-- Join tables (film ↔ metadata relationships)
-- ============================================================

CREATE TABLE IF NOT EXISTS film_genres (
    movie_id TEXT NOT NULL REFERENCES films(movie_id) ON DELETE CASCADE,
    genre_id INTEGER NOT NULL REFERENCES genres(genre_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

CREATE TABLE IF NOT EXISTS film_keywords (
    movie_id TEXT NOT NULL REFERENCES films(movie_id) ON DELETE CASCADE,
    keyword_id INTEGER NOT NULL REFERENCES keywords(keyword_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, keyword_id)
);

CREATE TABLE IF NOT EXISTS film_countries (
    movie_id TEXT NOT NULL REFERENCES films(movie_id) ON DELETE CASCADE,
    iso_3166_1 TEXT NOT NULL,
    name TEXT,
    PRIMARY KEY (movie_id, iso_3166_1)
);

CREATE TABLE IF NOT EXISTS film_cast (
    movie_id TEXT NOT NULL REFERENCES films(movie_id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    cast_order INTEGER,
    PRIMARY KEY (movie_id, person_id)
);

CREATE TABLE IF NOT EXISTS film_crew (
    movie_id TEXT NOT NULL REFERENCES films(movie_id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES people(person_id) ON DELETE CASCADE,
    job TEXT NOT NULL,             -- e.g. "Director", "Writer"
    department TEXT,
    PRIMARY KEY (movie_id, person_id, job)
);

-- ============================================================
-- Indexes (grouped by feature area)
-- ============================================================

-- User films lookups
CREATE INDEX IF NOT EXISTS idx_user_films_username ON user_films(username);
CREATE INDEX IF NOT EXISTS idx_user_films_movie_id ON user_films(movie_id);

-- Film search / filtering
CREATE INDEX IF NOT EXISTS idx_films_film_name ON films(film_name);
CREATE INDEX IF NOT EXISTS idx_films_release_year ON films(release_year);
CREATE INDEX IF NOT EXISTS idx_films_tmdb_id ON films(tmdb_id);

-- Metadata joins (useful for fingerprints)
CREATE INDEX IF NOT EXISTS idx_film_genres_genre_id ON film_genres(genre_id);
CREATE INDEX IF NOT EXISTS idx_film_keywords_keyword_id ON film_keywords(keyword_id);
CREATE INDEX IF NOT EXISTS idx_film_cast_person_id ON film_cast(person_id);
CREATE INDEX IF NOT EXISTS idx_film_crew_job ON film_crew(job);