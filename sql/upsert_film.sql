INSERT INTO films(movie_id, film_name, release_year, tmdb_id, tmdb_type, poster_path)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (movie_id)
DO UPDATE SET
  film_name = COALESCE(EXCLUDED.film_name, films.film_name),
  release_year = COALESCE(EXCLUDED.release_year, films.release_year),
  tmdb_id = COALESCE(EXCLUDED.tmdb_id, films.tmdb_id),
  tmdb_type = COALESCE(EXCLUDED.tmdb_type, films.tmdb_type),
  poster_path = COALESCE(EXCLUDED.poster_path, films.poster_path);