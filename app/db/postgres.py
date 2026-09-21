from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from dotenv import load_dotenv


load_dotenv()


DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


class DatabaseError(Exception):
    """Raised when a CasePilot database operation fails."""


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """
    Open a PostgreSQL connection using CasePilot environment settings.

    The connection is committed when the context exits successfully
    and rolled back automatically when an exception occurs.
    """
    try:
        with psycopg.connect(**DB_CONFIG) as connection:
            yield connection
    except psycopg.Error as exc:
        raise DatabaseError(
            f"PostgreSQL operation failed: {exc}"
        ) from exc


def fetch_one(
    query: str,
    params: tuple[Any, ...] = (),
) -> dict[str, Any] | None:
    """Execute a SELECT query and return one row as a dictionary."""
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)

                row = cursor.fetchone()

                if row is None:
                    return None

                columns = [column.name for column in cursor.description]

                return dict(zip(columns, row))

    except DatabaseError:
        raise
    except psycopg.Error as exc:
        raise DatabaseError(
            f"Failed to fetch database record: {exc}"
        ) from exc


def fetch_all(
    query: str,
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    """Execute a SELECT query and return all rows as dictionaries."""
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)

                rows = cursor.fetchall()

                columns = [column.name for column in cursor.description]

                return [
                    dict(zip(columns, row))
                    for row in rows
                ]

    except DatabaseError:
        raise
    except psycopg.Error as exc:
        raise DatabaseError(
            f"Failed to fetch database records: {exc}"
        ) from exc


def execute(
    query: str,
    params: tuple[Any, ...] = (),
) -> None:
    """Execute an INSERT, UPDATE, or DELETE statement."""
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)

    except DatabaseError:
        raise
    except psycopg.Error as exc:
        raise DatabaseError(
            f"Failed to execute database operation: {exc}"
        ) from exc