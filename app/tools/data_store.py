from __future__ import annotations

import csv
import json
from pathlib import Path
from functools import lru_cache
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class DataStoreError(Exception):
    """Raised when CasePilot data cannot be loaded or queried."""


def _read_csv(filename: str) -> list[dict[str, Any]]:
    path = DATA_DIR / filename

    if not path.exists():
        raise DataStoreError(
            f"Data file not found: {path}. "
            "Make sure the CasePilot data package is extracted into the project's data/ folder."
        )

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except OSError as exc:
        raise DataStoreError(f"Could not read {path}: {exc}") from exc


def _read_json(filename: str) -> dict[str, Any]:
    path = DATA_DIR / filename

    if not path.exists():
        raise DataStoreError(
            f"Policy file not found: {path}. "
            "Make sure the CasePilot data package is extracted into the project's data/ folder."
        )

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise DataStoreError(f"Could not read {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise DataStoreError(f"{path} must contain a JSON object.")

    return data


@lru_cache(maxsize=1)
def orders() -> list[dict[str, Any]]:
    return _read_csv("orders.csv")


@lru_cache(maxsize=1)
def payments() -> list[dict[str, Any]]:
    return _read_csv("payments.csv")


@lru_cache(maxsize=1)
def deliveries() -> list[dict[str, Any]]:
    return _read_csv("deliveries.csv")


@lru_cache(maxsize=1)
def returns() -> list[dict[str, Any]]:
    return _read_csv("returns.csv")


@lru_cache(maxsize=1)
def products() -> list[dict[str, Any]]:
    return _read_csv("products.csv")


@lru_cache(maxsize=1)
def refunds() -> list[dict[str, Any]]:
    return _read_csv("refunds.csv")


@lru_cache(maxsize=1)
def customers() -> list[dict[str, Any]]:
    return _read_csv("customers.csv")


@lru_cache(maxsize=1)
def amazon_policy() -> dict[str, Any]:
    return _read_json("amazon_policy.json")


@lru_cache(maxsize=1)
def casepilot_policy() -> dict[str, Any]:
    return _read_json("casepilot_policy.json")


def find_one(rows: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    value = str(value).strip()
    for row in rows:
        if str(row.get(key, "")).strip() == value:
            return row
    return None

def _write_csv(filename: str, rows: list[dict[str, Any]]) -> None:
    path = DATA_DIR / filename

    if not rows:
        raise DataStoreError(
            f"Cannot write empty dataset to {path}."
        )

    fieldnames = list(rows[0].keys())

    try:
        with path.open(
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames
            )

            writer.writeheader()
            writer.writerows(rows)

    except OSError as exc:
        raise DataStoreError(
            f"Could not write {path}: {exc}"
        ) from exc


def append_row(filename: str, row: dict[str, Any]) -> None:
    existing_rows = _read_csv(filename)

    if existing_rows:
        fieldnames = list(existing_rows[0].keys())

        missing = set(fieldnames) - set(row.keys())

        if missing:
            raise DataStoreError(
                f"Missing columns for {filename}: {sorted(missing)}"
            )

        new_row = {
            field: row.get(field, "")
            for field in fieldnames
        }

        existing_rows.append(new_row)

    else:
        existing_rows = [row]

    _write_csv(filename, existing_rows)

    # Clear cached data after modifying the file.
    if filename == "refunds.csv":
        refunds.cache_clear()

    elif filename == "orders.csv":
        orders.cache_clear()

    elif filename == "payments.csv":
        payments.cache_clear()

    elif filename == "deliveries.csv":
        deliveries.cache_clear()

    elif filename == "returns.csv":
        returns.cache_clear()

def update_one(
    filename: str,
    key: str,
    value: str,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Update one CSV row matching key=value.

    Returns the updated row, or None if no matching row exists.
    """

    rows = _read_csv(filename)

    target_value = str(value).strip()

    for row in rows:
        if str(row.get(key, "")).strip() == target_value:

            for field, new_value in updates.items():
                if field not in row:
                    raise DataStoreError(
                        f"Column '{field}' does not exist in {filename}."
                    )

                row[field] = str(new_value)

            _write_csv(filename, rows)

            # Clear cached data after modification.
            if filename == "refunds.csv":
                refunds.cache_clear()

            elif filename == "orders.csv":
                orders.cache_clear()

            elif filename == "payments.csv":
                payments.cache_clear()

            elif filename == "deliveries.csv":
                deliveries.cache_clear()

            elif filename == "returns.csv":
                returns.cache_clear()

            return row

    return None