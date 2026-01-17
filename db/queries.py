from pathlib import Path
from datetime import datetime, timezone
from db.connect import get_conn

def load_sql(filename: str) -> str:
    return Path("sql", filename).read_text(encoding="utf-8")

UPSERT_USER = load_sql("upsert_user.sql")
UPSERT_FILM = load_sql("upsert_film.sql")
UPSERT_USER_FILMS = load_sql("upsert_user_films.sql")
UPSERT_LIKED_COUNTS = load_sql("upsert_liked_review_counts.sql")

def upsert_user(username: str, display_name: str, reviews_written : int | None):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(UPSERT_USER, (username, display_name, reviews_written, now))
        conn.commit()

def upsert_films(films: dict[str, dict]):
    """
    films: dict keyed by movie_id with values like:
      {"film_name": "...", "release_year": None, "tmdb_id": None, "tmdb_type": None, "poster_path": None}
    """
    values = []
    for movie_id, meta in films.items():
        values.append((
            str(movie_id),
            meta.get("film_name"),
            meta.get("release_year"),
            meta.get("tmdb_id"),
            meta.get("tmdb_type"),
            meta.get("poster_path"),
        ))

    if not values:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_FILM, values)
        conn.commit()

def upsert_user_films(username: str, rows: list[dict]):
    values = []
    for r in rows:
        values.append((
            username,
            str(r["movie_id"]),
            bool(r["watched"]),
            bool(r["in_watchlist"]),
            None if r.get("rating_val") is None else float(r["rating_val"]),
            bool(r["liked"]),
            bool(r["has_review"]),
        ))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_USER_FILMS, values)
        conn.commit()

def upsert_liked_review_counts(liker_username: str, counts: dict[str, int] | list[dict]):
    values = []
    if isinstance(counts, dict):
        for author, cnt in counts.items():
            values.append((liker_username, author, int(cnt)))
    else:
        for item in counts:
            values.append((liker_username, item["author_username"], int(item["liked_count"])))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_LIKED_COUNTS, values)
        conn.commit()