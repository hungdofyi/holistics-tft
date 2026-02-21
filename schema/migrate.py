"""Run SQL migrations against the database."""

import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def run_migration(filepath: str) -> None:
    database_url = os.environ["DATABASE_URL"]
    with open(filepath) as f:
        sql = f.read()
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print(f"Migration applied: {filepath}")
    finally:
        conn.close()


if __name__ == "__main__":
    migration_file = sys.argv[1] if len(sys.argv) > 1 else "schema/migrations/001_initial.sql"
    run_migration(migration_file)
