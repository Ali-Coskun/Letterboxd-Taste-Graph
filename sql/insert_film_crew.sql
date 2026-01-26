INSERT INTO film_crew(movie_id, person_id, job, department)
VALUES (%s, %s, %s, %s)
ON CONFLICT (movie_id, person_id, job)
DO UPDATE SET
  department = COALESCE(EXCLUDED.department, film_crew.department);