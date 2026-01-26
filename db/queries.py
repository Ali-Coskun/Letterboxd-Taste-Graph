from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Iterable, Mapping, Any

from db.connect import get_conn


# ----------------------------
# SQL loader (robust pathing)
# ----------------------------

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def load_sql(filename: str) -> str:
    path = _SQL_DIR / filename
    return path.read_text(encoding="utf-8")


def _try_load_sql(filename: str) -> Optional[str]:
    path = _SQL_DIR / filename
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


# ----------------------------
# Load SQL files
# ----------------------------

UPSERT_USER = load_sql("upsert_user.sql")
UPSERT_FILM = load_sql("upsert_film.sql")
UPSERT_USER_FILMS = load_sql("upsert_user_films.sql")
UPSERT_LIKED_COUNTS = load_sql("upsert_liked_review_counts.sql")

UPSERT_GENRE = load_sql("upsert_genre.sql")
UPSERT_KEYWORD = load_sql("upsert_keyword.sql")
UPSERT_PERSON = load_sql("upsert_person.sql")

INSERT_FILM_GENRE = load_sql("insert_film_genre.sql")
INSERT_FILM_KEYWORD = load_sql("insert_film_keyword.sql")
INSERT_FILM_COUNTRY = load_sql("insert_film_country.sql")
INSERT_FILM_CAST = load_sql("insert_film_cast.sql")
INSERT_FILM_CREW = load_sql("insert_film_crew.sql")

DELETE_FILM_JOINS = load_sql("delete_film_joins.sql")

# Optional: only works if you add this file later
# sql/upsert_user_mutual.sql (recommended)
UPSERT_USER_MUTUAL = _try_load_sql("upsert_user_mutual.sql")


# ----------------------------
# Core upserts
# ----------------------------

def upsert_user(username: str,
                display_name: Optional[str] = None,
                reviews_written: int = 0) -> None:
    """
    Upserts a user row. (reviews_written is required by schema, defaults to 0)
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(UPSERT_USER, (username, display_name, int(reviews_written), now))
        conn.commit()


def upsert_films(films: Mapping[str, Mapping[str, Any]]) -> None:
    """
    Upserts films by movie_id.

    Expects meta keys matching your schema/upsert_film.sql:
      film_name, release_year, release_date, runtime_minutes,
      original_language, overview, poster_path, backdrop_path,
      tmdb_id, tmdb_type, imdb_id, tmdb_vote_average, tmdb_vote_count

    You can pass only what you have; missing values can be None.
    """
    values = []
    for movie_id, meta in films.items():
        values.append((
            str(movie_id),
            meta.get("film_name"),
            meta.get("release_year"),
            meta.get("release_date"),
            meta.get("runtime_minutes"),
            meta.get("original_language"),
            meta.get("overview"),
            meta.get("poster_path"),
            meta.get("backdrop_path"),
            meta.get("tmdb_id"),
            meta.get("tmdb_type"),
            meta.get("imdb_id"),
            meta.get("tmdb_vote_average"),
            meta.get("tmdb_vote_count"),
        ))

    if not values:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_FILM, values)
        conn.commit()


def upsert_user_films(username: str, rows: list[dict]) -> None:
    """
    Upserts (username, movie_id) facts.

    Each row must contain:
      movie_id, watched, in_watchlist, rating_val, liked, has_review
    """
    values = []
    for r in rows:
        values.append((
            username,
            str(r["movie_id"]),
            bool(r["watched"]),
            bool(r["in_watchlist"]),
            None if r.get("rating_val") is None else float(r["rating_val"]),
            bool(r.get("liked", False)),        # liked is NOT NULL in schema
            bool(r.get("has_review", False)),
        ))

    if not values:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_USER_FILMS, values)
        conn.commit()


def upsert_liked_review_counts(liker_username: str,
                              counts: dict[str, int] | list[dict]) -> None:
    """
    Upserts aggregated counts: liker_username -> author_username -> liked_count
    """
    values = []
    if isinstance(counts, dict):
        for author, cnt in counts.items():
            values.append((liker_username, author, int(cnt)))
    else:
        for item in counts:
            values.append((liker_username, item["author_username"], int(item["liked_count"])))

    if not values:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_LIKED_COUNTS, values)
        conn.commit()


# ----------------------------
# Lookup tables (genre/keyword/person)
# ----------------------------

def upsert_genres(genres: Mapping[int, str] | Iterable[dict]) -> None:
    """
    Accepts either:
      {genre_id: name, ...}
    or:
      [{"genre_id": 28, "name": "Action"}, ...]
    """
    values = []
    if isinstance(genres, dict):
        for gid, name in genres.items():
            values.append((int(gid), str(name)))
    else:
        for g in genres:
            values.append((int(g["genre_id"]), str(g["name"])))

    if not values:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_GENRE, values)
        conn.commit()


def upsert_keywords(keywords: Mapping[int, str] | Iterable[dict]) -> None:
    """
    Accepts either:
      {keyword_id: name, ...}
    or:
      [{"keyword_id": 123, "name": "time travel"}, ...]
    """
    values = []
    if isinstance(keywords, dict):
        for kid, name in keywords.items():
            values.append((int(kid), str(name)))
    else:
        for k in keywords:
            values.append((int(k["keyword_id"]), str(k["name"])))

    if not values:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_KEYWORD, values)
        conn.commit()


def upsert_people(people: Mapping[int, str] | Iterable[dict]) -> None:
    """
    Accepts either:
      {person_id: name, ...}
    or:
      [{"person_id": 287, "name": "Brad Pitt"}, ...]
    """
    values = []
    if isinstance(people, dict):
        for pid, name in people.items():
            values.append((int(pid), str(name)))
    else:
        for p in people:
            values.append((int(p["person_id"]), str(p["name"])))

    if not values:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_PERSON, values)
        conn.commit()


# ----------------------------
# Join tables (film -> metadata)
# ----------------------------

def delete_film_joins(movie_id: str) -> None:
    """
    Clears all join rows for a movie so you can re-insert from fresh TMDb metadata.
    Your delete_film_joins.sql contains multiple DELETE statements.
    """
    # Split and execute statement-by-statement
    stmts = [s.strip() for s in DELETE_FILM_JOINS.split(";") if s.strip()]

    with get_conn() as conn:
        with conn.cursor() as cur:
            for stmt in stmts:
                cur.execute(stmt, (movie_id,))
        conn.commit()


def insert_film_genres(movie_id: str, genre_ids: Iterable[int]) -> None:
    values = [(movie_id, int(gid)) for gid in genre_ids]
    if not values:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(INSERT_FILM_GENRE, values)
        conn.commit()


def insert_film_keywords(movie_id: str, keyword_ids: Iterable[int]) -> None:
    values = [(movie_id, int(kid)) for kid in keyword_ids]
    if not values:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(INSERT_FILM_KEYWORD, values)
        conn.commit()


def insert_film_countries(movie_id: str, countries: Iterable[dict]) -> None:
    """
    countries items like:
      {"iso_3166_1": "US", "name": "United States of America"}
    """
    values = []
    for c in countries:
        values.append((movie_id, c.get("iso_3166_1"), c.get("name")))
    if not values:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(INSERT_FILM_COUNTRY, values)
        conn.commit()


def insert_film_cast(movie_id: str, cast: Iterable[dict]) -> None:
    """
    cast items like:
      {"person_id": 287, "cast_order": 0}
    """
    values = []
    for c in cast:
        values.append((movie_id, int(c["person_id"]), c.get("cast_order")))
    if not values:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(INSERT_FILM_CAST, values)
        conn.commit()


def insert_film_crew(movie_id: str, crew: Iterable[dict]) -> None:
    """
    crew items like:
      {"person_id": 525, "job": "Director", "department": "Directing"}
    """
    values = []
    for c in crew:
        values.append((movie_id, int(c["person_id"]), str(c["job"]), c.get("department")))
    if not values:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(INSERT_FILM_CREW, values)
        conn.commit()


# ----------------------------
# Optional: mutual edges
# ----------------------------

def upsert_user_mutuals(username: str,
                        mutual_usernames: Iterable[str],
                        fetched_at: Optional[datetime] = None) -> None:
    """
    Requires you to create:
      sql/upsert_user_mutual.sql
    and the corresponding table in schema.sql.

    This function will raise a clear error if the SQL file isn't present yet.
    """
    if UPSERT_USER_MUTUAL is None:
        raise RuntimeError(
            "Missing sql/upsert_user_mutual.sql. Create the edge-table SQL file first."
        )

    ts = fetched_at or datetime.now(timezone.utc).replace(tzinfo=None)
    values = [(username, m, ts) for m in mutual_usernames if m and m != username]
    if not values:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_USER_MUTUAL, values)
        conn.commit()