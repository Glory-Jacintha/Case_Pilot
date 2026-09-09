from __future__ import annotations

from datetime import datetime

from langchain.tools import tool

from app.tools.data_store import (
    orders,
    payments,
    refunds,
    append_row,
    update_one,
    find_one,
)


def _next_refund_id() -> str:
    """
    Generate the next synthetic refund ID based on
    the highest existing numeric refund ID.
    """

    highest_number = 0

    for refund in refunds():
        refund_id = str(refund.get("RefundID", ""))

        if refund_id.startswith("REF"):
            try:
                number = int(refund[3:])
                highest_number = max(highest_number, number)
            except ValueError:
                continue

    return f"REF{highest_number + 1:08d}"


@tool
def create_refund(
    order_id: str,
    amount: float,
    reason: str,
) -> dict:
    """
    Create or initiate a synthetic refund for a CasePilot order.

    This modifies only the local CasePilot synthetic dataset.
    It does NOT interact with Amazon, banks, payment gateways,
    or any real financial system.

    If an existing refund record has NOT_INITIATED status,
    that record is updated instead of creating a duplicate.

    Args:
        order_id: The order ID.
        amount: The amount to refund.
        reason: The reason for the refund.
    """

    # =========================================================
    # 1. Find the order
    # =========================================================

    order = find_one(
        orders(),
        "OrderID",
        order_id,
    )

    if not order:
        return {
            "success": False,
            "error_code": "ORDER_NOT_FOUND",
            "message": f"Order {order_id} was not found.",
        }

    # =========================================================
    # 2. Validate order amount
    # =========================================================

    try:
        order_amount = float(order["TotalAmount"])
    except (ValueError, TypeError, KeyError):
        return {
            "success": False,
            "error_code": "INVALID_ORDER_AMOUNT",
            "message": (
                f"The amount for order {order_id} "
                "could not be determined."
            ),
        }

    if amount <= 0:
        return {
            "success": False,
            "error_code": "INVALID_REFUND_AMOUNT",
            "message": "Refund amount must be greater than zero.",
        }

    if amount > order_amount:
        return {
            "success": False,
            "error_code": "REFUND_EXCEEDS_ORDER_AMOUNT",
            "message": (
                f"Requested refund ₹{amount:.2f} exceeds "
                f"the order amount ₹{order_amount:.2f}."
            ),
        }

    # =========================================================
    # 3. Find successful payment
    # =========================================================

    payment = find_one(
        payments(),
        "OrderID",
        order_id,
    )

    if not payment:
        return {
            "success": False,
            "error_code": "PAYMENT_NOT_FOUND",
            "message": (
                f"No payment record was found for {order_id}."
            ),
        }

    payment_status = str(
        payment.get("PaymentStatus", "")
    ).upper()

    if payment_status != "SUCCESS":
        return {
            "success": False,
            "error_code": "PAYMENT_NOT_SUCCESSFUL",
            "message": (
                f"Payment status is "
                f"{payment_status or 'UNKNOWN'}; "
                "refund cannot be created."
            ),
        }

    # =========================================================
    # 4. Check existing refund
    # =========================================================

    existing_refund = find_one(
        refunds(),
        "OrderID",
        order_id,
    )

    if existing_refund:

        existing_status = str(
            existing_refund.get("RefundStatus", "")
        ).upper()

        existing_amount = float(
            existing_refund.get("RefundAmount", 0) or 0
        )

        # -----------------------------------------------------
        # Already completed
        # -----------------------------------------------------

        if existing_status == "COMPLETED":
            return {
                "success": False,
                "error_code": "REFUND_ALREADY_COMPLETED",
                "message": (
                    f"Refund {existing_refund.get('RefundID')} "
                    f"has already been completed."
                ),
            }

        # -----------------------------------------------------
        # Already processing
        # -----------------------------------------------------

        if existing_status == "PROCESSING":
            return {
                "success": False,
                "error_code": "REFUND_ALREADY_PROCESSING",
                "message": (
                    f"Refund {existing_refund.get('RefundID')} "
                    f"is already being processed."
                ),
            }

        # -----------------------------------------------------
        # Existing NOT_INITIATED refund
        # -----------------------------------------------------

        if existing_status == "NOT_INITIATED":

            if abs(existing_amount - amount) > 0.01:
                return {
                    "success": False,
                    "error_code": "REFUND_AMOUNT_MISMATCH",
                    "message": (
                        f"Existing refund amount is "
                        f"₹{existing_amount:.2f}, but "
                        f"₹{amount:.2f} was requested."
                    ),
                }

            now = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            updated = update_one(
                "refunds.csv",
                "RefundID",
                existing_refund["RefundID"],
                {
                    "RefundStatus": "PROCESSING",
                    "RefundReason": reason,
                    "RequestedDate": now,
                },
            )

            if not updated:
                return {
                    "success": False,
                    "error_code": "REFUND_UPDATE_FAILED",
                    "message": (
                        "The existing refund could not be updated."
                    ),
                }

            return {
                "success": True,
                "operation": "UPDATE_REFUND",
                "refund_id": existing_refund["RefundID"],
                "order_id": order_id,
                "amount": amount,
                "status": "PROCESSING",
                "reason": reason,
                "message": (
                    f"Existing refund "
                    f"{existing_refund['RefundID']} "
                    f"was moved from NOT_INITIATED "
                    f"to PROCESSING."
                ),
            }

    # =========================================================
    # 5. No existing refund → create a new one
    # =========================================================

    refund_id = _next_refund_id()

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    new_refund = {
        "RefundID": refund_id,
        "OrderID": order_id,
        "CustomerID": order.get("CustomerID", ""),
        "TransactionID": payment.get(
            "TransactionID",
            "",
        ),
        "RefundAmount": str(amount),
        "RefundStatus": "PROCESSING",
        "RefundReason": reason,
        "RequestedDate": now,
        "ProcessedDate": "",
        "GatewayReference": "",
    }

    append_row(
        "refunds.csv",
        new_refund,
    )

    return {
        "success": True,
        "operation": "CREATE_REFUND",
        "refund_id": refund_id,
        "order_id": order_id,
        "amount": amount,
        "status": "PROCESSING",
        "reason": reason,
        "message": (
            f"Refund {refund_id} was created successfully "
            f"for ₹{amount:.2f}."
        ),
    }