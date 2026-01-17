import re
import logging
import get_user_ratings
import get_user_watchlist

logger = logging.getLogger(__name__)
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{1,30}$")  # adjust if LB allows hyphens


def get_user_film(username: str):
    if not isinstance(username, str) or not USERNAME_RE.match(username):
        return [], "bad_username"

    films, films_status = get_user_ratings.get_ratings_data(username)
    watchlist, watch_status = get_user_watchlist.get_watchlist_data(username)

    if films_status != "success":
        return [], films_status
    if watch_status != "success":
        return [], watch_status

    user_film = []

    # Ratings / watched list
    for film in films:
        user_film.append(
            {
                "movie_id": film.get("movie_id"),
                "watched": True,
                "in_watchlist": False,
                "rating_val": film.get("rating_val", None),
                "liked": film.get("liked", None),
                "has_review": film.get("has_review", False),  # already computed by your scraper
            }
        )

    # Watchlist list
    for film in watchlist:
        user_film.append(
            {
                "movie_id": film.get("movie_id"),
                "watched": False,
                "in_watchlist": True,
                "rating_val": None,
                "liked": None,
                "has_review": False,
            }
        )

    return user_film, "success"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    username = "Dcsoeirvy"
    user_film, status = get_user_film(username)
    print(status, len(user_film))
    for film in user_film:
        print(film)