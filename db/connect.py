import os
from dotenv import load_dotenv
import psycopg

load_dotenv()

def get_conn():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set. Put it in .env")
    return psycopg.connect(url)

print(get_conn())