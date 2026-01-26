INSERT INTO users(username, display_name, reviews_written, last_fetched_at)
VALUES (%s, %s, %s, %s)
ON CONFLICT (username)
DO UPDATE SET
  display_name = COALESCE(EXCLUDED.display_name, users.display_name),
  reviews_written = EXCLUDED.reviews_written,
  last_fetched_at = EXCLUDED.last_fetched_at;