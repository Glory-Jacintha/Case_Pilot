import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

conn = psycopg.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "postgres"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)

with conn.cursor() as cur:
    print("COLUMNS:")
    cur.execute("""
        SELECT
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_name = 'case_history_examples'
        ORDER BY ordinal_position;
    """)

    for row in cur.fetchall():
        print(row)

    print("\nINDEXES:")
    cur.execute("""
        SELECT
            indexname,
            indexdef
        FROM pg_indexes
        WHERE tablename = 'case_history_examples';
    """)

    for row in cur.fetchall():
        print(row)

conn.close()
