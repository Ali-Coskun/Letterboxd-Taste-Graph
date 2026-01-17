INSERT INTO user_films(
  username, movie_id, watched, in_watchlist, rating_val, liked, has_review
)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (username, movie_id)
DO UPDATE SET
  watched = EXCLUDED.watched,
  in_watchlist = EXCLUDED.in_watchlist,
  rating_val = EXCLUDED.rating_val,
  liked = EXCLUDED.liked,
  has_review = EXCLUDED.has_review;