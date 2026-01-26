INSERT INTO film_keywords(movie_id, keyword_id)
VALUES (%s, %s)
ON CONFLICT DO NOTHING;