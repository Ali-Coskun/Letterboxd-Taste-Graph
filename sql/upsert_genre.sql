INSERT INTO genres(genre_id, name)
VALUES (%s, %s)
ON CONFLICT (genre_id)
DO UPDATE SET
  name = EXCLUDED.name;