DELETE FROM film_genres WHERE movie_id = %s;
DELETE FROM film_keywords WHERE movie_id = %s;
DELETE FROM film_countries WHERE movie_id = %s;
DELETE FROM film_cast WHERE movie_id = %s;
DELETE FROM film_crew WHERE movie_id = %s;