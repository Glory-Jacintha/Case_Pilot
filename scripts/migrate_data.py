import csv
import os
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal

import psycopg
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

BATCH_SIZE = 2000


# ============================================================
# HELPERS
# ============================================================

def clean(value):
    """Convert empty CSV values to None."""
    if value is None:
        return None

    value = value.strip()

    if value == "":
        return None

    return value


def to_int(value):
    value = clean(value)

    if value is None:
        return None

    # Non-numeric / unavailable values
    if value.upper() in {"N/A", "NA", "NONE", "NULL", "-"}:
        return None

    try:
        return int(value)
    except ValueError:
        pass

    # Handle values such as:
    # "Attempt 1"
    # "Attempt 2"
    # "Attempt 3"
    parts = value.split()

    for part in reversed(parts):
        try:
            return int(part)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse integer: {value}")


def to_decimal(value):
    value = clean(value)
    return Decimal(value) if value is not None else None


def to_float(value):
    value = clean(value)
    return float(value) if value is not None else None


def to_bool(value):
    value = clean(value)

    if value is None:
        return None

    return value.lower() in {
        "true",
        "1",
        "yes",
        "y",
        "t",
    }


def to_date(value):
    value = clean(value)

    if value is None:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d",
        "%Y/%m/%d %H:%M:%S",
        "%d-%m-%Y",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Unable to parse date: {value}")


def to_timestamp(value):
    value = clean(value)

    if value is None:
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    # Also support ISO timestamps with timezone information.
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        pass

    raise ValueError(f"Unable to parse timestamp: {value}")


def read_csv(filename):
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def insert_batches(cur, sql, rows, table_name):
    """Insert rows in batches."""
    total = len(rows)

    for start in range(0, total, BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        cur.executemany(sql, batch)

        processed = min(start + BATCH_SIZE, total)

        print(
            f"  {table_name}: "
            f"{processed:,}/{total:,}"
        )


# ============================================================
# CUSTOMERS
# ============================================================

def migrate_customers(cur):
    rows = read_csv("customers.csv")

    data = [
        (
            clean(row["CustomerID"]),
            clean(row["CustomerName"]),
            clean(row["City"]),
            clean(row["State"]),
            clean(row["Country"]),
        )
        for row in rows
    ]

    sql = """
        INSERT INTO customers (
            customer_id,
            customer_name,
            city,
            state,
            country
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (customer_id) DO NOTHING
    """

    insert_batches(cur, sql, data, "customers")


# ============================================================
# PRODUCTS
# ============================================================

def migrate_products(cur):
    rows = read_csv("products.csv")

    data = [
        (
            clean(row["ProductID"]),
            clean(row["ProductName"]),
            clean(row["Category"]),
            clean(row["Brand"]),
            to_int(row["ReturnWindowDays"]),
            to_bool(row["ReturnEligible"]),
            to_bool(row["ReturnlessRefundEligible"]),
            clean(row["NonReturnableReason"]),
        )
        for row in rows
    ]

    sql = """
        INSERT INTO products (
            product_id,
            product_name,
            category,
            brand,
            return_window_days,
            return_eligible,
            returnless_refund_eligible,
            non_returnable_reason
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (product_id) DO NOTHING
    """

    insert_batches(cur, sql, data, "products")


# ============================================================
# ORDERS
# ============================================================

def migrate_orders(cur):
    rows = read_csv("orders.csv")

    data = [
        (
            clean(row["OrderID"]),
            to_timestamp(row["OrderDate"]),
            clean(row["CustomerID"]),
            clean(row["CustomerName"]),
            clean(row["ProductID"]),
            clean(row["ProductName"]),
            clean(row["Category"]),
            clean(row["Brand"]),
            to_int(row["Quantity"]),
            to_decimal(row["UnitPrice"]),
            to_decimal(row["Discount"]),
            to_decimal(row["Tax"]),
            to_decimal(row["ShippingCost"]),
            to_decimal(row["TotalAmount"]),
            clean(row["PaymentMethod"]),
            clean(row["OrderStatus"]),
            clean(row["City"]),
            clean(row["State"]),
            clean(row["Country"]),
            clean(row["SellerID"]),
        )
        for row in rows
    ]

    sql = """
        INSERT INTO orders (
            order_id,
            order_date,
            customer_id,
            customer_name,
            product_id,
            product_name,
            category,
            brand,
            quantity,
            unit_price,
            discount,
            tax,
            shipping_cost,
            total_amount,
            payment_method,
            order_status,
            city,
            state,
            country,
            seller_id
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (order_id) DO NOTHING
    """

    insert_batches(cur, sql, data, "orders")


# ============================================================
# PAYMENTS
# ============================================================

def migrate_payments(cur):
    rows = read_csv("payments.csv")

    data = [
        (
            clean(row["TransactionID"]),
            clean(row["OrderID"]),
            clean(row["CustomerID"]),
            to_decimal(row["Amount"]),
            clean(row["PaymentMethod"]),
            clean(row["PaymentStatus"]),
            to_timestamp(row["TransactionDate"]),
            clean(row["GatewayReference"]),
        )
        for row in rows
    ]

    sql = """
        INSERT INTO payments (
            transaction_id,
            order_id,
            customer_id,
            amount,
            payment_method,
            payment_status,
            transaction_date,
            gateway_reference
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (transaction_id) DO NOTHING
    """

    insert_batches(cur, sql, data, "payments")


# ============================================================
# DELIVERIES
# ============================================================

def migrate_deliveries(cur):
    rows = read_csv("deliveries.csv")

    data = [
        (
            clean(row["DeliveryID"]),
            clean(row["OrderID"]),
            clean(row["TrackingID"]),
            clean(row["DeliveryStatus"]),
            to_date(row["ExpectedDate"]),
            to_date(row["ActualDeliveryDate"]),
            clean(row["Courier"]),
            to_int(row["DeliveryAttempts"]),
            clean(row["DeliveryProof"]),
        )
        for row in rows
    ]

    sql = """
        INSERT INTO deliveries (
            delivery_id,
            order_id,
            tracking_id,
            delivery_status,
            expected_date,
            actual_delivery_date,
            courier,
            delivery_attempts,
            delivery_proof
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (delivery_id) DO NOTHING
    """

    insert_batches(cur, sql, data, "deliveries")


# ============================================================
# RETURNS
# ============================================================

def migrate_returns(cur):
    rows = read_csv("returns.csv")

    data = [
        (
            clean(row["ReturnID"]),
            clean(row["OrderID"]),
            clean(row["CustomerID"]),
            clean(row["ReturnStatus"]),
            clean(row["ReturnReason"]),
            to_date(row["RequestedDate"]),
            to_date(row["ApprovedDate"]),
        )
        for row in rows
    ]

    sql = """
        INSERT INTO returns (
            return_id,
            order_id,
            customer_id,
            return_status,
            return_reason,
            requested_date,
            approved_date
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (return_id) DO NOTHING
    """

    insert_batches(cur, sql, data, "returns")


# ============================================================
# REFUNDS
# ============================================================

def migrate_refunds(cur):
    rows = read_csv("refunds.csv")

    data = [
        (
            clean(row["RefundID"]),
            clean(row["OrderID"]),
            clean(row["CustomerID"]),
            clean(row["TransactionID"]),
            to_decimal(row["RefundAmount"]),
            clean(row["RefundStatus"]),
            clean(row["RefundReason"]),
            to_date(row["RequestedDate"]),
            to_date(row["ProcessedDate"]),
            clean(row["GatewayReference"]),
        )
        for row in rows
    ]

    sql = """
        INSERT INTO refunds (
            refund_id,
            order_id,
            customer_id,
            transaction_id,
            refund_amount,
            refund_status,
            refund_reason,
            requested_date,
            processed_date,
            gateway_reference
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (refund_id) DO NOTHING
    """

    insert_batches(cur, sql, data, "refunds")


# ============================================================
# SUPPORT CASES
# ============================================================

def migrate_support_cases(cur):
    rows = read_csv("support_cases.csv")

    data = [
        (
            clean(row["case_id"]),
            clean(row["customer_id"]),
            clean(row["order_id"]),
            clean(row["customer_message"]),
            clean(row["domain"]),
            clean(row["issue_type"]),
            clean(row["support_category"]),
            clean(row["product_name"]),
            clean(row["product_category"]),
            to_decimal(row["transaction_amount"]),
            clean(row["order_status"]),
            to_timestamp(row["reported_at"]),
            clean(row["channel"]),
            to_float(row["historical_csat"]),
            clean(row["amount_band"]),
        )
        for row in rows
    ]

    sql = """
        INSERT INTO support_cases (
            case_id,
            customer_id,
            order_id,
            customer_message,
            domain,
            issue_type,
            support_category,
            product_name,
            product_category,
            transaction_amount,
            order_status,
            reported_at,
            channel,
            historical_csat,
            amount_band
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        ON CONFLICT (case_id) DO NOTHING
    """

    insert_batches(cur, sql, data, "support_cases")


# ============================================================
# RESOLUTION STRATEGIES
# ============================================================

def migrate_resolution_strategies(cur):
    rows = read_csv("resolution_strategies.csv")

    data = [
        (
            clean(row["domain"]),
            clean(row["strategy_id"]),
            clean(row["description"]),
            clean(row["tool_sequence"]),
            clean(row["action_type"]),
        )
        for row in rows
    ]

    sql = """
        INSERT INTO resolution_strategies (
            domain,
            strategy_id,
            description,
            tool_sequence,
            action_type
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (domain, strategy_id) DO NOTHING
    """

    insert_batches(
        cur,
        sql,
        data,
        "resolution_strategies",
    )


# ============================================================
# CASE HISTORY
# ============================================================

def migrate_case_history(cur):
    rows = read_csv("case_history_examples.csv")

    data = [
        (
            clean(row["case_id"]),
            clean(row["scenario"]),
            clean(row["domain"]),
            clean(row["case_description"]),
            clean(row["attempt"]),
            clean(row["result"]),
            clean(row["reason_or_next_step"]),
        )
        for row in rows
    ]

    sql = """
        INSERT INTO case_history_examples (
            case_id,
            scenario,
            domain,
            case_description,
            attempt,
            result,
            reason_or_next_step
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (case_id) DO NOTHING
    """

    insert_batches(
        cur,
        sql,
        data,
        "case_history_examples",
    )


# ============================================================
# DATA DICTIONARY
# ============================================================

def migrate_data_dictionary(cur):
    rows = read_csv("data_dictionary.csv")

    data = [
        (
            clean(row["file"]),
            clean(row["purpose"]),
            clean(row["important_fields"]),
        )
        for row in rows
    ]

    sql = """
        INSERT INTO data_dictionary (
            file,
            purpose,
            important_fields
        )
        VALUES (%s, %s, %s)
        ON CONFLICT (file) DO NOTHING
    """

    insert_batches(
        cur,
        sql,
        data,
        "data_dictionary",
    )


# ============================================================
# ROW COUNT VERIFICATION
# ============================================================

EXPECTED_COUNTS = {
    "customers": 100000,
    "products": 50,
    "orders": 100000,
    "payments": 100000,
    "deliveries": 100000,
    "returns": 3054,
    "refunds": 6083,
    "support_cases": 80093,
    "resolution_strategies": 8,
    "case_history_examples": 15,
    "data_dictionary": 12,
}


def verify_counts(cur):
    print("\n" + "=" * 60)
    print("ROW COUNT VERIFICATION")
    print("=" * 60)

    all_ok = True

    for table, expected in EXPECTED_COUNTS.items():
        cur.execute(
            f"SELECT COUNT(*) FROM {table}"
        )

        actual = cur.fetchone()[0]

        status = "OK" if actual == expected else "CHECK"

        print(
            f"{table:<28} "
            f"{actual:>8,} / {expected:>8,} "
            f"[{status}]"
        )

        if actual != expected:
            all_ok = False

    return all_ok


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("CASEPILOT RDS DATA MIGRATION")
    print("=" * 60)

    print(f"\nData directory: {DATA_DIR}")
    print(f"Batch size: {BATCH_SIZE:,}")

    with psycopg.connect(**DB_CONFIG) as conn:

        print("\nConnected to RDS successfully.")

        with conn.cursor() as cur:

            print("\nStarting migration...\n")

            # Dependency order is important.
            migrate_customers(cur)
            migrate_products(cur)
            migrate_orders(cur)
            migrate_payments(cur)
            migrate_deliveries(cur)
            migrate_returns(cur)
            migrate_refunds(cur)
            migrate_support_cases(cur)
            migrate_resolution_strategies(cur)
            migrate_case_history(cur)
            migrate_data_dictionary(cur)

            conn.commit()

            print("\nMigration committed successfully.")

            counts_ok = verify_counts(cur)

            if not counts_ok:
                raise RuntimeError(
                    "One or more row counts do not match "
                    "the expected dataset counts."
                )

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    main()