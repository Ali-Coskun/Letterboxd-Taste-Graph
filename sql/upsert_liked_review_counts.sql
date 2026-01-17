INSERT INTO liked_review_counts(liker_username, author_username, liked_count)
VALUES (%s, %s, %s)
ON CONFLICT (liker_username, author_username)
DO UPDATE SET
  liked_count = EXCLUDED.liked_count;