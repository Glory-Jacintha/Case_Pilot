import os

import psycopg
from dotenv import load_dotenv


load_dotenv()


def test_rds_connection():
    connection = psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=10,
    )

    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]

    print("\nConnected to PostgreSQL successfully!")
    print(f"Database: {os.getenv('DB_NAME')}")
    print(f"Host: {os.getenv('DB_HOST')}")
    print(f"PostgreSQL: {version}")

    connection.close()