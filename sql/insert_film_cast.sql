INSERT INTO film_cast(movie_id, person_id, cast_order)
VALUES (%s, %s, %s)
ON CONFLICT (movie_id, person_id)
DO UPDATE SET
  cast_order = COALESCE(EXCLUDED.cast_order, film_cast.cast_order);