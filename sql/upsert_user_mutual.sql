INSERT INTO user_mutuals(username, mutual_username, fetched_at)
VALUES (%s, %s, %s)
ON CONFLICT (username, mutual_username)
DO UPDATE SET
  fetched_at = EXCLUDED.fetched_at;