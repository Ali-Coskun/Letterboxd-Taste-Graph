CREATE TABLE IF NOT EXISTS users(
    username TEXT PRIMARY KEY,
    display_name TEXT,
    reviews_written INTEGER NOT NULL DEFAULT 0,
    last_fetched_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS films (
  movie_id TEXT PRIMARY KEY,
  film_name TEXT,
  release_year INTEGER,
  tmdb_id INTEGER,
  tmdb_type TEXT,
  poster_path TEXT
);

CREATE TABLE IF NOT EXISTS user_films(
    username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    movie_id TEXT NOT NULL REFERENCES films(movie_id) ON DELETE CASCADE,

    watched BOOLEAN NOT NULL,
    in_watchlist BOOLEAN NOT NULL,
    rating_val REAL,
    liked BOOLEAN NOT NULL,
    has_review BOOLEAN NOT NULL,

    PRIMARY KEY (username, movie_id)
);

CREATE TABLE IF NOT EXISTS liked_review_count(
    liker_username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    author_username TEXT NOT NULL,
    liked_count INTEGER NOT NULL,

    PRIMARY KEY (liker_username, author_username)
);

CREATE INDEX IF NOT EXISTS idx_user_films_movie_id ON user_films(movie_id);
CREATE INDEX IF NOT EXISTS idx_user_films_username ON user_films(username);
CREATE INDEX IF NOT EXISTS idx_films_film_name ON films(film_name);

ALTER TABLE users
ADD COLUMN IF NOT EXISTS display_name TEXT;

ALTER TABLE users
ADD COLUMN IF NOT EXISTS reviews_written INTEGER NOT NULL DEFAULT 0;