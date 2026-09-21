from __future__ import annotations

import os

import psycopg
from dotenv import load_dotenv


load_dotenv()


def main():
    connection = psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)

            tables = cursor.fetchall()

        print("Connected to RDS successfully!")
        print("\nTables in PostgreSQL:\n")

        for (table_name,) in tables:
            print(f"  - {table_name}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()