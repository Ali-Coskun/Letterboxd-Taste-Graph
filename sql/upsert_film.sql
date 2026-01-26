INSERT INTO films(
  movie_id, film_name, release_year, release_date, runtime_minutes,
  original_language, overview, poster_path, backdrop_path,
  tmdb_id, tmdb_type, imdb_id,
  tmdb_vote_average, tmdb_vote_count
)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (movie_id)
DO UPDATE SET
  film_name = COALESCE(EXCLUDED.film_name, films.film_name),
  release_year = COALESCE(EXCLUDED.release_year, films.release_year),
  release_date = COALESCE(EXCLUDED.release_date, films.release_date),
  runtime_minutes = COALESCE(EXCLUDED.runtime_minutes, films.runtime_minutes),
  original_language = COALESCE(EXCLUDED.original_language, films.original_language),
  overview = COALESCE(EXCLUDED.overview, films.overview),
  poster_path = COALESCE(EXCLUDED.poster_path, films.poster_path),
  backdrop_path = COALESCE(EXCLUDED.backdrop_path, films.backdrop_path),
  tmdb_id = COALESCE(EXCLUDED.tmdb_id, films.tmdb_id),
  tmdb_type = COALESCE(EXCLUDED.tmdb_type, films.tmdb_type),
  imdb_id = COALESCE(EXCLUDED.imdb_id, films.imdb_id),
  tmdb_vote_average = COALESCE(EXCLUDED.tmdb_vote_average, films.tmdb_vote_average),
  tmdb_vote_count = COALESCE(EXCLUDED.tmdb_vote_count, films.tmdb_vote_count);