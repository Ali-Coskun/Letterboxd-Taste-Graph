from pathlib import Path
from db.connect import get_conn

def run_schema(schema_path: str = "sql/schema.sql"):
    # Always resolve schema.sql relative to the project root
    project_root = Path(__file__).resolve().parent.parent  # .../db -> project root
    full_path = project_root / schema_path                 # .../schema.sql

    sql_text = full_path.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]

    with get_conn() as conn:
        with conn.cursor() as cur:   # NOTE: cursor() not cursor
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()

if __name__ == "__main__":
    run_schema()
    print("✅ schema.sql applied successfully")