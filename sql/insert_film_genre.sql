INSERT INTO film_genres(movie_id, genre_id)
VALUES (%s, %s)
ON CONFLICT DO NOTHING;