from __future__ import annotations

from typing import Any

from app.tools.data_store import (
    find_one,
    orders,
    payments,
    refunds,
)


def _customer_has_received_refund(
    state,
    refund: dict[str, Any],
) -> bool:
    """
    Determine whether the customer's refund issue
    has actually been resolved.

    A COMPLETED refund means the refund outcome has
    been completed.

    PROCESSING is not treated as completed for a
    customer who says the refund has not been received.
    """

    refund_status = str(
        refund.get("RefundStatus", "")
    ).upper()

    customer_message = str(
        state.get("customer_message", "")
    ).lower()

    not_received_phrases = [
        "haven't received",
        "have not received",
        "not received",
        "didn't receive",
        "did not receive",
        "still waiting",
        "waiting for refund",
        "refund is pending",
        "refund pending",
        "refund hasn't arrived",
        "refund has not arrived",
    ]

    customer_is_waiting = any(
        phrase in customer_message
        for phrase in not_received_phrases
    )

    if customer_is_waiting:
        return refund_status == "COMPLETED"

    # For a normal refund request, successful initiation
    # is enough to consider the requested operation completed.
    return refund_status in {
        "PROCESSING",
        "COMPLETED",
    }


def validate_resolution(
    state,
) -> dict[str, Any]:
    """
    Validate whether the strategy actually resolved
    the customer's business problem.

    This is deliberately separate from tool success.
    """

    issue_type = str(
        state.get("issue_type", "")
    ).upper()

    order_id = state.get("order_id")

    if not order_id:

        return {
            "resolution_success": False,
            "resolution_failure_reason": (
                "Order ID is required to validate "
                "the resolution."
            ),
            "status": "RESOLUTION_VALIDATION_FAILED",
        }

    # =========================================================
    # REFUND VALIDATION
    # =========================================================

    if "REFUND" in issue_type:

        order = find_one(
            orders(),
            "OrderID",
            order_id,
        )

        if not order:

            return {
                "resolution_success": False,
                "resolution_failure_reason": (
                    f"Order {order_id} could not be "
                    "found during resolution validation."
                ),
                "status": "RESOLUTION_VALIDATION_FAILED",
            }

        payment = find_one(
            payments(),
            "OrderID",
            order_id,
        )

        if not payment:

            return {
                "resolution_success": False,
                "resolution_failure_reason": (
                    "Payment information could not be "
                    "verified during validation."
                ),
                "status": "RESOLUTION_VALIDATION_FAILED",
            }

        refund = find_one(
            refunds(),
            "OrderID",
            order_id,
        )

        if not refund:

            return {
                "resolution_success": False,
                "resolution_failure_reason": (
                    "No refund record exists after "
                    "the resolution attempt."
                ),
                "status": "RESOLUTION_VALIDATION_FAILED",
            }

        refund_status = str(
            refund.get("RefundStatus", "")
        ).upper()

        resolved = _customer_has_received_refund(
            state,
            refund,
        )

        if resolved:

            return {
                "resolution_success": True,
                "resolution_result": {
                    "operation": "REFUND_VALIDATED",
                    "order_id": order_id,
                    "refund_id": refund.get(
                        "RefundID",
                        "",
                    ),
                    "refund_status": refund_status,
                    "amount": float(
                        refund.get(
                            "RefundAmount",
                            0,
                        )
                        or 0
                    ),
                },
                "resolution_failure_reason": "",
                "status": "RESOLUTION_COMPLETED",
            }

        return {
            "resolution_success": False,
            "resolution_failure_reason": (
                f"Refund {refund.get('RefundID', '')} "
                f"is currently {refund_status}. "
                "The customer's refund has not yet "
                "reached COMPLETED status."
            ),
            "status": "RESOLUTION_VALIDATION_FAILED",
        }

    # =========================================================
    # GENERIC VALIDATION
    # =========================================================

    result = state.get(
        "resolution_result",
        {},
    )

    if result.get("success"):

        return {
            "resolution_success": True,
            "resolution_failure_reason": "",
            "status": "RESOLUTION_COMPLETED",
        }

    return {
        "resolution_success": False,
        "resolution_failure_reason": (
            "The resolution strategy did not produce "
            "a successful business outcome."
        ),
        "status": "RESOLUTION_VALIDATION_FAILED",
    }