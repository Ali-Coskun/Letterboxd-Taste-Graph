INSERT INTO keywords(keyword_id, name)
VALUES (%s, %s)
ON CONFLICT (keyword_id)
DO UPDATE SET
  name = EXCLUDED.name;