INSERT INTO people(person_id, name)
VALUES (%s, %s)
ON CONFLICT (person_id)
DO UPDATE SET
  name = EXCLUDED.name;