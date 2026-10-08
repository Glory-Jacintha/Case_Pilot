"""
CasePilot - Fresh Test Case Discovery

This script is READ-ONLY.

It uses the existing CasePilot PostgreSQL connection and discovers
fresh RDS records suitable for end-to-end UI testing.

It does NOT:
- INSERT
- UPDATE
- DELETE
- cancel orders
- create refunds
- process returns

It only executes SELECT queries.
"""

from __future__ import annotations

from typing import Any

from app.db.postgres import fetch_all, DatabaseError


# -------------------------------------------------------------------
# Previously used IDs
# -------------------------------------------------------------------

USED_ORDER_IDS = (
    "ORD0000001",
    "ORD0000164",
    "ORD0000293",
)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def format_money(value: Any) -> str:
    """Format a database amount safely."""

    if value is None:
        return "N/A"

    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def print_section(title: str) -> None:
    """Print a clear section heading."""

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_records(records: list[dict[str, Any]]) -> None:
    """Print records in a readable format."""

    if not records:
        print("No matching records found.")
        return

    for index, record in enumerate(records, start=1):
        print(f"\n[{index}]")

        for key, value in record.items():

            if key in {"total_amount", "refund_amount", "payment_amount"}:
                value = format_money(value)

            print(f"  {key}: {value}")


# -------------------------------------------------------------------
# Common SQL exclusion
# -------------------------------------------------------------------

ORDER_EXCLUSION = """
    o.order_id NOT IN (
        'ORD0000001',
        'ORD0000164',
        'ORD0000293'
    )
"""


# -------------------------------------------------------------------
# 1. ORDER
# -------------------------------------------------------------------

def find_order_cases() -> list[dict[str, Any]]:
    """
    Find fresh orders for basic ORDER domain testing.
    """

    query = f"""
        SELECT
            o.order_id,
            o.customer_id,
            o.product_id,
            o.total_amount,
            o.order_status,
            o.order_date,
            p.payment_status,
            d.delivery_status
        FROM orders o

        LEFT JOIN LATERAL (
            SELECT
                payment_status
            FROM payments p
            WHERE p.order_id = o.order_id
            ORDER BY p.transaction_date DESC NULLS LAST
            LIMIT 1
        ) p ON TRUE

        LEFT JOIN LATERAL (
            SELECT
                delivery_status
            FROM deliveries d
            WHERE d.order_id = o.order_id
            ORDER BY d.actual_delivery_date DESC NULLS LAST
            LIMIT 1
        ) d ON TRUE

        WHERE {ORDER_EXCLUSION}

        ORDER BY RANDOM()
        LIMIT 5;
    """

    return fetch_all(query)


# -------------------------------------------------------------------
# 2. PAYMENT
# -------------------------------------------------------------------

def find_payment_cases() -> list[dict[str, Any]]:
    """
    Find fresh orders with payment records.

    These are useful for:
    - payment status
    - payment verification
    - payment reconciliation
    """

    query = f"""
        SELECT
            o.order_id,
            o.customer_id,
            o.total_amount,
            o.order_status,
            p.transaction_id,
            p.amount AS payment_amount,
            p.payment_status,
            p.transaction_date
        FROM orders o

        INNER JOIN LATERAL (
            SELECT
                transaction_id,
                amount,
                payment_status,
                transaction_date
            FROM payments p
            WHERE p.order_id = o.order_id
            ORDER BY p.transaction_date DESC NULLS LAST
            LIMIT 1
        ) p ON TRUE

        WHERE {ORDER_EXCLUSION}

        ORDER BY RANDOM()
        LIMIT 5;
    """

    return fetch_all(query)


# -------------------------------------------------------------------
# 3. DELIVERY
# -------------------------------------------------------------------

def find_delivery_cases() -> list[dict[str, Any]]:
    """
    Find fresh orders with delivery records.
    """

    query = f"""
        SELECT
            o.order_id,
            o.customer_id,
            o.total_amount,
            o.order_status,
            d.delivery_id,
            d.tracking_id,
            d.delivery_status,
            d.actual_delivery_date
        FROM orders o

        INNER JOIN LATERAL (
            SELECT
                delivery_id,
                tracking_id,
                delivery_status,
                actual_delivery_date
            FROM deliveries d
            WHERE d.order_id = o.order_id
            ORDER BY d.actual_delivery_date DESC NULLS LAST
            LIMIT 1
        ) d ON TRUE

        WHERE {ORDER_EXCLUSION}

        ORDER BY RANDOM()
        LIMIT 5;
    """

    return fetch_all(query)


# -------------------------------------------------------------------
# 4. LOW-VALUE REFUND
# -------------------------------------------------------------------

def find_low_value_refund_cases() -> list[dict[str, Any]]:
    """
    Find fresh refund candidates below the ₹2,000
    autonomous transaction threshold.

    These are useful for testing:
        AI_ALLOWED
        refund eligibility
        refund initiation
        validation
    """

    query = f"""
        SELECT
            o.order_id,
            o.customer_id,
            o.product_id,
            o.total_amount,
            o.order_status,

            p.payment_status,

            pr.product_name,
            pr.return_eligible,

            rf.refund_id,
            rf.refund_amount,
            rf.refund_status

        FROM orders o

        INNER JOIN LATERAL (
            SELECT
                payment_status
            FROM payments p
            WHERE p.order_id = o.order_id
            ORDER BY p.transaction_date DESC NULLS LAST
            LIMIT 1
        ) p ON TRUE

        LEFT JOIN products pr
            ON pr.product_id = o.product_id

        LEFT JOIN LATERAL (
            SELECT
                refund_id,
                refund_amount,
                refund_status
            FROM refunds rf
            WHERE rf.order_id = o.order_id
            ORDER BY rf.requested_date DESC NULLS LAST
            LIMIT 1
        ) rf ON TRUE

        WHERE
            {ORDER_EXCLUSION}

            AND o.total_amount < 2000

            AND p.payment_status = 'SUCCESS'

            AND (
                rf.refund_id IS NULL
                OR rf.refund_status NOT IN (
                    'COMPLETED',
                    'SUCCESS'
                )
            )

        ORDER BY RANDOM()
        LIMIT 5;
    """

    return fetch_all(query)


# -------------------------------------------------------------------
# 5. HIGH-VALUE REFUND
# -------------------------------------------------------------------

def find_high_value_refund_cases() -> list[dict[str, Any]]:
    """
    Find fresh refund candidates at or above ₹2,000.

    These are useful for testing:
        HUMAN_REQUIRED
        LangGraph interrupt
        Human Review UI
        Approve
        Reject
    """

    query = f"""
        SELECT
            o.order_id,
            o.customer_id,
            o.product_id,
            o.total_amount,
            o.order_status,

            p.payment_status,

            pr.product_name,
            pr.return_eligible,

            rf.refund_id,
            rf.refund_amount,
            rf.refund_status

        FROM orders o

        INNER JOIN LATERAL (
            SELECT
                payment_status
            FROM payments p
            WHERE p.order_id = o.order_id
            ORDER BY p.transaction_date DESC NULLS LAST
            LIMIT 1
        ) p ON TRUE

        LEFT JOIN products pr
            ON pr.product_id = o.product_id

        LEFT JOIN LATERAL (
            SELECT
                refund_id,
                refund_amount,
                refund_status
            FROM refunds rf
            WHERE rf.order_id = o.order_id
            ORDER BY rf.requested_date DESC NULLS LAST
            LIMIT 1
        ) rf ON TRUE

        WHERE
            {ORDER_EXCLUSION}

            AND o.total_amount >= 2000

            AND p.payment_status = 'SUCCESS'

            AND (
                rf.refund_id IS NULL
                OR rf.refund_status NOT IN (
                    'COMPLETED',
                    'SUCCESS'
                )
            )

        ORDER BY RANDOM()
        LIMIT 5;
    """

    return fetch_all(query)


# -------------------------------------------------------------------
# 6. RETURN
# -------------------------------------------------------------------

def find_return_cases() -> list[dict[str, Any]]:
    """
    Find fresh orders whose product is marked return eligible.

    Prefer delivered orders without an existing completed return.
    """

    query = f"""
        SELECT
            o.order_id,
            o.customer_id,
            o.product_id,
            o.total_amount,
            o.order_status,

            pr.product_name,
            pr.return_eligible,
            pr.return_window_days,

            d.delivery_status,

            r.return_id,
            r.return_status

        FROM orders o

        INNER JOIN products pr
            ON pr.product_id = o.product_id

        LEFT JOIN LATERAL (
            SELECT
                delivery_status
            FROM deliveries d
            WHERE d.order_id = o.order_id
            ORDER BY d.actual_delivery_date DESC NULLS LAST
            LIMIT 1
        ) d ON TRUE

        LEFT JOIN LATERAL (
            SELECT
                return_id,
                return_status
            FROM returns r
            WHERE r.order_id = o.order_id
            ORDER BY r.requested_date DESC NULLS LAST
            LIMIT 1
        ) r ON TRUE

        WHERE
            {ORDER_EXCLUSION}

            AND pr.return_eligible = TRUE

            AND (
                r.return_id IS NULL
                OR r.return_status NOT IN (
                    'COMPLETED',
                    'RECEIVED'
                )
            )

        ORDER BY RANDOM()
        LIMIT 5;
    """

    return fetch_all(query)


# -------------------------------------------------------------------
# 7. CANCELLATION
# -------------------------------------------------------------------

def find_cancellation_cases() -> list[dict[str, Any]]:
    """
    Find fresh orders that are not already cancelled,
    returned, or delivered.

    These are better candidates for cancellation testing.
    """

    query = f"""
        SELECT
            o.order_id,
            o.customer_id,
            o.product_id,
            o.total_amount,
            o.order_status,
            o.order_date,

            p.payment_status,

            pr.product_name,
            pr.return_eligible

        FROM orders o

        LEFT JOIN LATERAL (
            SELECT
                payment_status
            FROM payments p
            WHERE p.order_id = o.order_id
            ORDER BY p.transaction_date DESC NULLS LAST
            LIMIT 1
        ) p ON TRUE

        LEFT JOIN products pr
            ON pr.product_id = o.product_id

        WHERE
            {ORDER_EXCLUSION}

            AND o.order_status NOT IN (
                'Cancelled',
                'Returned',
                'Delivered'
            )

        ORDER BY RANDOM()
        LIMIT 5;
    """

    return fetch_all(query)


# -------------------------------------------------------------------
# 8. PRODUCT QUERY
# -------------------------------------------------------------------

def find_product_cases() -> list[dict[str, Any]]:
    """
    Find fresh products for PRODUCT_QUERY testing.

    Uses only columns that exist in the CasePilot products table.
    """

    query = """
        SELECT
            product_id,
            product_name,
            category,
            return_eligible,
            return_window_days
        FROM products
        ORDER BY RANDOM()
        LIMIT 5;
    """

    return fetch_all(query)


# -------------------------------------------------------------------
# 9. CROSS-DOMAIN WORKFLOW
# -------------------------------------------------------------------

def find_cross_domain_cases() -> list[dict[str, Any]]:
    """
    Find cases suitable for testing:

        ORDER
          ↓
        CANCELLATION
          ↓
        RETURN
          ↓
        REFUND
          ↓
        HUMAN APPROVAL

    We specifically look for:
    - order not already cancelled/returned/delivered
    - amount >= ₹2,000
    - successful payment
    - return-eligible product
    - no completed refund
    """

    query = f"""
        SELECT
            o.order_id,
            o.customer_id,
            o.product_id,
            o.total_amount,
            o.order_status,

            p.payment_status,

            pr.product_name,
            pr.return_eligible,
            pr.return_window_days,

            rf.refund_id,
            rf.refund_status

        FROM orders o

        INNER JOIN LATERAL (
            SELECT
                payment_status
            FROM payments p
            WHERE p.order_id = o.order_id
            ORDER BY p.transaction_date DESC NULLS LAST
            LIMIT 1
        ) p ON TRUE

        INNER JOIN products pr
            ON pr.product_id = o.product_id

        LEFT JOIN LATERAL (
            SELECT
                refund_id,
                refund_status
            FROM refunds rf
            WHERE rf.order_id = o.order_id
            ORDER BY rf.requested_date DESC NULLS LAST
            LIMIT 1
        ) rf ON TRUE

        WHERE
            {ORDER_EXCLUSION}

            AND o.total_amount >= 2000

            AND o.order_status NOT IN (
                'Cancelled',
                'Returned',
                'Delivered'
            )

            AND p.payment_status = 'SUCCESS'

            AND pr.return_eligible = TRUE

            AND (
                rf.refund_id IS NULL
                OR rf.refund_status NOT IN (
                    'COMPLETED',
                    'SUCCESS'
                )
            )

        ORDER BY RANDOM()
        LIMIT 5;
    """

    return fetch_all(query)


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

def main() -> None:
    print()
    print("=" * 80)
    print("CASEPILOT - FRESH RDS TEST DATA DISCOVERY")
    print("=" * 80)

    print()
    print("Database mode : READ-ONLY")
    print("Previously used orders:")
    for order_id in USED_ORDER_IDS:
        print(f"  - {order_id}")

    print()
    print("Searching RDS for fresh test records...")

    try:

        # -----------------------------------------------------------
        # ORDER
        # -----------------------------------------------------------

        print_section("1. ORDER TEST CASES")

        order_cases = find_order_cases()
        print_records(order_cases)

        # -----------------------------------------------------------
        # PAYMENT
        # -----------------------------------------------------------

        print_section("2. PAYMENT TEST CASES")

        payment_cases = find_payment_cases()
        print_records(payment_cases)

        # -----------------------------------------------------------
        # DELIVERY
        # -----------------------------------------------------------

        print_section("3. DELIVERY TEST CASES")

        delivery_cases = find_delivery_cases()
        print_records(delivery_cases)

        # -----------------------------------------------------------
        # LOW VALUE REFUND
        # -----------------------------------------------------------

        print_section(
            "4. LOW-VALUE REFUND TEST CASES (< ₹2,000)"
        )

        low_refund_cases = find_low_value_refund_cases()
        print_records(low_refund_cases)

        # -----------------------------------------------------------
        # HIGH VALUE REFUND
        # -----------------------------------------------------------

        print_section(
            "5. HIGH-VALUE REFUND TEST CASES (≥ ₹2,000)"
        )

        high_refund_cases = find_high_value_refund_cases()
        print_records(high_refund_cases)

        # -----------------------------------------------------------
        # RETURN
        # -----------------------------------------------------------

        print_section("6. RETURN TEST CASES")

        return_cases = find_return_cases()
        print_records(return_cases)

        # -----------------------------------------------------------
        # CANCELLATION
        # -----------------------------------------------------------

        print_section("7. CANCELLATION TEST CASES")

        cancellation_cases = find_cancellation_cases()
        print_records(cancellation_cases)

        # -----------------------------------------------------------
        # PRODUCT QUERY
        # -----------------------------------------------------------

        print_section("8. PRODUCT QUERY TEST CASES")

        product_cases = find_product_cases()
        print_records(product_cases)

        # -----------------------------------------------------------
        # CROSS DOMAIN
        # -----------------------------------------------------------

        print_section(
            "9. CROSS-DOMAIN WORKFLOW TEST CASES"
        )

        cross_domain_cases = find_cross_domain_cases()
        print_records(cross_domain_cases)

        # -----------------------------------------------------------
        # SUMMARY
        # -----------------------------------------------------------

        print_section("DISCOVERY SUMMARY")

        print(
            f"ORDER cases found           : {len(order_cases)}"
        )

        print(
            f"PAYMENT cases found         : {len(payment_cases)}"
        )

        print(
            f"DELIVERY cases found        : {len(delivery_cases)}"
        )

        print(
            f"LOW-VALUE REFUND cases     : {len(low_refund_cases)}"
        )

        print(
            f"HIGH-VALUE REFUND cases    : {len(high_refund_cases)}"
        )

        print(
            f"RETURN cases found          : {len(return_cases)}"
        )

        print(
            f"CANCELLATION cases found    : {len(cancellation_cases)}"
        )

        print(
            f"PRODUCT cases found         : {len(product_cases)}"
        )

        print(
            f"CROSS-DOMAIN cases found    : {len(cross_domain_cases)}"
        )

        print()
        print("=" * 80)
        print("DISCOVERY COMPLETE")
        print("=" * 80)

        print()
        print(
            "No database records were modified."
        )

        print(
            "Send the complete terminal output to me."
        )

        print(
            "I will turn these records into the CasePilot UI "
            "test sequence."
        )

    except DatabaseError as exc:
        print()
        print("=" * 80)
        print("DATABASE ERROR")
        print("=" * 80)
        print()
        print(str(exc))
        print()
        print(
            "Check that your .env contains the same RDS "
            "configuration used by CasePilot."
        )

    except Exception as exc:
        print()
        print("=" * 80)
        print("UNEXPECTED ERROR")
        print("=" * 80)
        print()
        print(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()