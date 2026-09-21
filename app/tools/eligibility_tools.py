from __future__ import annotations

from datetime import date, datetime, timedelta

from langchain.tools import tool

from app.db.postgres import DatabaseError, fetch_all, fetch_one


def _parse_date(value: str) -> date | None:
    value = str(value).strip()

    if not value:
        return None

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


@tool
def check_refund_eligibility(
    order_id: str,
    request_date: str = "",
) -> dict:
    """
    Check whether an order appears eligible for a refund using
    CasePilot's configured eligibility rules and RDS business data.

    request_date should be YYYY-MM-DD when a return-window check
    is relevant.
    """

    try:
        order_id = str(order_id).strip()

        # =========================================================
        # 1. Find order
        # =========================================================

        order = fetch_one(
            """
            SELECT
                order_id,
                order_date,
                customer_id,
                product_id,
                total_amount,
                order_status
            FROM orders
            WHERE order_id = %s
            """,
            (order_id,),
        )

        if not order:
            return {
                "success": False,
                "eligible": False,
                "reason": "Order not found.",
            }

        # =========================================================
        # 2. Find payment
        # =========================================================

        payment = fetch_one(
            """
            SELECT
                transaction_id,
                amount,
                payment_status
            FROM payments
            WHERE order_id = %s
            ORDER BY transaction_date DESC
            LIMIT 1
            """,
            (order_id,),
        )

        if not payment:
            return {
                "success": True,
                "eligible": False,
                "reason": "No payment record exists for the order.",
            }

        if payment.get("payment_status") != "SUCCESS":
            return {
                "success": True,
                "eligible": False,
                "reason": (
                    f"Payment status is "
                    f"{payment.get('payment_status')}, not SUCCESS."
                ),
            }

        # =========================================================
        # 3. Check existing refunds
        # =========================================================

        refund_records = fetch_all(
            """
            SELECT
                refund_id,
                refund_amount,
                refund_status
            FROM refunds
            WHERE order_id = %s
            ORDER BY requested_date DESC NULLS LAST
            """,
            (order_id,),
        )

        if any(
            str(refund.get("refund_status", "")).upper() == "COMPLETED"
            for refund in refund_records
        ):
            return {
                "success": True,
                "eligible": False,
                "reason": (
                    "A completed refund already exists for this order."
                ),
            }

        # =========================================================
        # 4. Find product
        # =========================================================

        product = fetch_one(
            """
            SELECT
                product_id,
                return_window_days,
                return_eligible,
                returnless_refund_eligible,
                non_returnable_reason
            FROM products
            WHERE product_id = %s
            """,
            (str(order.get("product_id", "")).strip(),),
        )

        # =========================================================
        # 5. Find return
        # =========================================================

        return_record = fetch_one(
            """
            SELECT
                return_id,
                return_status,
                return_reason,
                requested_date,
                approved_date
            FROM returns
            WHERE order_id = %s
            ORDER BY requested_date DESC NULLS LAST
            LIMIT 1
            """,
            (order_id,),
        )

        # =========================================================
        # 6. Cancelled order
        # =========================================================

        status = str(order.get("order_status", "")).strip()

        if status == "Cancelled":
            return {
                "success": True,
                "eligible": True,
                "reason": (
                    "Order is cancelled, payment succeeded, "
                    "and no completed refund exists."
                ),
                "checks": {
                    "order_cancelled": True,
                    "payment_successful": True,
                    "completed_refund": False,
                },
                "amount": float(order.get("total_amount") or 0),
            }

        # =========================================================
        # 7. Returned order
        # =========================================================

        if status == "Returned":

            if not return_record:
                return {
                    "success": True,
                    "eligible": False,
                    "reason": (
                        "Order is marked Returned but no return "
                        "record was found."
                    ),
                }

            return_status = str(
                return_record.get("return_status", "")
            ).upper()

            if return_status not in {"RECEIVED", "COMPLETED"}:
                return {
                    "success": True,
                    "eligible": False,
                    "reason": (
                        "Return exists but the item has not reached "
                        "a RECEIVED/COMPLETED state required for "
                        "this prototype's refund path."
                    ),
                }

            return {
                "success": True,
                "eligible": True,
                "reason": (
                    "Returned item is recorded as received/completed "
                    "and payment succeeded."
                ),
                "amount": float(order.get("total_amount") or 0),
            }

        # =========================================================
        # 8. Non-returnable product
        # =========================================================

        if (
            product
            and product.get("return_eligible") is False
        ):
            return {
                "success": True,
                "eligible": False,
                "reason": (
                    "Product is marked non-returnable in "
                    "the product policy metadata."
                ),
                "exception_check_required": True,
                "non_returnable_reason": (
                    product.get("non_returnable_reason") or ""
                ),
            }

        # =========================================================
        # 9. Return-window check
        # =========================================================

        if request_date and product:

            order_date = order.get("order_date")

            if isinstance(order_date, datetime):
                order_date = order_date.date()

            requested = _parse_date(request_date)

            window = int(
                product.get("return_window_days") or 30
            )

            if not order_date or not requested:
                return {
                    "success": True,
                    "eligible": False,
                    "reason": (
                        "Could not parse the order/request date "
                        "for the return-window check."
                    ),
                }

            deadline = order_date + timedelta(days=window)

            if requested > deadline:
                return {
                    "success": True,
                    "eligible": False,
                    "reason": (
                        f"Request is outside the configured "
                        f"{window}-day product return window."
                    ),
                    "deadline": deadline.isoformat(),
                }

        # =========================================================
        # 10. No blocking condition
        # =========================================================

        return {
            "success": True,
            "eligible": True,
            "reason": (
                "No blocking eligibility condition was detected "
                "by the available data."
            ),
            "amount": float(order.get("total_amount") or 0),
        }

    except (DatabaseError, ValueError, TypeError) as exc:
        return {
            "success": False,
            "eligible": False,
            "reason": str(exc),
        }