INSERT INTO film_countries(movie_id, iso_3166_1, name)
VALUES (%s, %s, %s)
ON CONFLICT (movie_id, iso_3166_1)
DO UPDATE SET
  name = COALESCE(EXCLUDED.name, film_countries.name);