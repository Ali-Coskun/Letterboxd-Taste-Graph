import asyncio
import get_user_film
import get_user_liked_reviews
import get_user_mutuals

def get_mutuals_ingestion(user):

    user_film, user_film_status = get_user_film(user)
    liked_reviews, liked_reviews_status = get_user_liked_reviews.reviews_liked_from_user(user)

    followers, following, mutuals = asyncio.run(get_user_mutuals.get_mutuals_for_user(user))

    for mutal in mutuals:
        user_film, user_film_status = get_user_film(mutal)
        liked_reviews, liked_reviews_status = get_user_liked_reviews.reviews_liked_from_user(mutal)

