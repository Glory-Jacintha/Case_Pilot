from __future__ import annotations

from datetime import date, datetime, timedelta

from langchain.tools import tool

from .data_store import (
    DataStoreError,
    find_one,
    orders,
    payments,
    products,
    refunds,
    returns,
)


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
def check_refund_eligibility(order_id: str, request_date: str = "") -> dict:
    """Check whether an order appears eligible for a refund using CasePilot's configured policy checks and the available order/payment/return/product data. request_date should be YYYY-MM-DD when a return-window check is relevant."""
    try:
        order = find_one(orders(), "OrderID", order_id)
        if not order:
            return {"success": False, "eligible": False, "reason": "Order not found."}

        payment = find_one(payments(), "OrderID", order_id)
        if not payment:
            return {
                "success": True,
                "eligible": False,
                "reason": "No payment record exists for the order.",
            }

        if payment.get("PaymentStatus") != "SUCCESS":
            return {
                "success": True,
                "eligible": False,
                "reason": f"Payment status is {payment.get('PaymentStatus')}, not SUCCESS.",
            }

        refund_records = [r for r in refunds() if r.get("OrderID") == str(order_id).strip()]
        if any(r.get("RefundStatus") == "COMPLETED" for r in refund_records):
            return {
                "success": True,
                "eligible": False,
                "reason": "A completed refund already exists for this order.",
            }

        product = find_one(products(), "ProductID", order.get("ProductID", ""))
        return_record = find_one(returns(), "OrderID", order_id)

        status = order.get("OrderStatus")
        if status == "Cancelled":
            return {
                "success": True,
                "eligible": True,
                "reason": "Order is cancelled, payment succeeded, and no completed refund exists.",
                "checks": {
                    "order_cancelled": True,
                    "payment_successful": True,
                    "completed_refund": False,
                },
                "amount": float(order.get("TotalAmount") or 0),
            }

        if status == "Returned":
            if not return_record:
                return {
                    "success": True,
                    "eligible": False,
                    "reason": "Order is marked Returned but no return record was found.",
                }

            if return_record.get("ReturnStatus") not in {"RECEIVED", "COMPLETED"}:
                return {
                    "success": True,
                    "eligible": False,
                    "reason": (
                        "Return exists but the item has not reached a RECEIVED/COMPLETED "
                        "state required for this prototype's refund path."
                    ),
                }

            return {
                "success": True,
                "eligible": True,
                "reason": "Returned item is recorded as received/completed and payment succeeded.",
                "amount": float(order.get("TotalAmount") or 0),
            }

        if product and str(product.get("ReturnEligible", "")).lower() == "false":
            return {
                "success": True,
                "eligible": False,
                "reason": "Product is marked non-returnable in the product policy metadata.",
                "exception_check_required": True,
                "non_returnable_reason": product.get("NonReturnableReason", ""),
            }

        if request_date and product:
            order_date = _parse_date(order.get("OrderDate", ""))
            requested = _parse_date(request_date)
            window = int(float(product.get("ReturnWindowDays") or 30))

            if not order_date or not requested:
                return {
                    "success": True,
                    "eligible": False,
                    "reason": "Could not parse the order/request date for the return-window check.",
                }

            deadline = order_date + timedelta(days=window)
            if requested > deadline:
                return {
                    "success": True,
                    "eligible": False,
                    "reason": f"Request is outside the configured {window}-day product return window.",
                    "deadline": deadline.isoformat(),
                }

        return {
            "success": True,
            "eligible": True,
            "reason": "No blocking eligibility condition was detected by the available data.",
            "amount": float(order.get("TotalAmount") or 0),
        }

    except (DataStoreError, ValueError, TypeError) as exc:
        return {"success": False, "eligible": False, "reason": str(exc)}
