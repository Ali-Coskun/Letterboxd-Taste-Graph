CREATE TABLE IF NOT EXISTS users(
    username TEXT PRIMARY KEY,
    last_fetched_at TIMESTAMP 
    -- add display name later
    -- also add reviews written
);

CREATE TABLE IF NOT EXISTS user_films(
    username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    movie_id TEXT NOT NULL,

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