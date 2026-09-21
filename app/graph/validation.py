from __future__ import annotations

from typing import Any

from app.tools.read_tools import (
    get_order_details,
    get_payment_details,
    get_delivery_details,
    get_return_details,
    get_refund_details,
    get_product_details,
)


# ============================================================
# Generic validation helpers
# ============================================================

def _failure(reason: str) -> dict[str, Any]:
    return {
        "resolution_success": False,
        "resolution_failure_reason": reason,
        "status": "RESOLUTION_VALIDATION_FAILED",
    }


def _success(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "resolution_success": True,
        "resolution_result": result,
        "resolution_failure_reason": "",
        "status": "RESOLUTION_COMPLETED",
    }


# ============================================================
# ORDER VALIDATION
# ============================================================

def _validate_order(
    state: dict[str, Any],
) -> dict[str, Any]:

    order_id = state.get("order_id")

    if not order_id:
        return _failure(
            "Order ID is required to validate the order resolution."
        )

    result = get_order_details.invoke(
        {"order_id": str(order_id)}
    )

    if not result.get("success"):
        return _failure(
            result.get(
                "message",
                f"Order {order_id} could not be found during validation.",
            )
        )

    order = result.get("order", {})

    return _success(
        {
            "operation": "ORDER_INFORMATION_VALIDATED",
            "order_id": order.get("order_id", order_id),
            "order_status": order.get("order_status", ""),
            "amount": float(
                order.get("total_amount", 0) or 0
            ),
        }
    )


# ============================================================
# PAYMENT VALIDATION
# ============================================================

def _validate_payment(
    state: dict[str, Any],
) -> dict[str, Any]:

    order_id = state.get("order_id")

    if not order_id:
        return _failure(
            "Order ID is required to validate the payment."
        )

    result = get_payment_details.invoke(
        {"order_id": str(order_id)}
    )

    if not result.get("success"):
        return _failure(
            result.get(
                "message",
                f"Payment information for order {order_id} "
                "could not be found.",
            )
        )

    payment = result.get("payment", {})

    return _success(
        {
            "operation": "PAYMENT_INFORMATION_VALIDATED",
            "order_id": payment.get("order_id", order_id),
            "transaction_id": payment.get("transaction_id", ""),
            "payment_status": payment.get("payment_status", ""),
            "amount": float(
                payment.get("amount", 0) or 0
            ),
        }
    )


# ============================================================
# DELIVERY VALIDATION
# ============================================================

def _validate_delivery(
    state: dict[str, Any],
) -> dict[str, Any]:

    order_id = state.get("order_id")

    if not order_id:
        return _failure(
            "Order ID is required to validate the delivery."
        )

    result = get_delivery_details.invoke(
        {"order_id": str(order_id)}
    )

    if not result.get("success"):
        return _failure(
            result.get(
                "message",
                f"Delivery information for order {order_id} "
                "could not be found.",
            )
        )

    delivery = result.get("delivery", {})

    return _success(
        {
            "operation": "DELIVERY_INFORMATION_VALIDATED",
            "order_id": delivery.get("order_id", order_id),
            "delivery_status": delivery.get(
                "delivery_status",
                "",
            ),
            "tracking_id": delivery.get(
                "tracking_id",
                "",
            ),
            "courier": delivery.get(
                "courier",
                "",
            ),
        }
    )


# ============================================================
# REFUND HELPER
# ============================================================

def _customer_waiting_for_refund(
    state: dict[str, Any],
) -> bool:

    message = str(
        state.get("customer_message", "")
    ).lower()

    waiting_phrases = (
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
    )

    return any(
        phrase in message
        for phrase in waiting_phrases
    )


# ============================================================
# REFUND VALIDATION
# ============================================================

def _validate_refund(
    state: dict[str, Any],
) -> dict[str, Any]:

    order_id = state.get("order_id")

    if not order_id:
        return _failure(
            "Order ID is required to validate the refund resolution."
        )

    # --------------------------------------------------------
    # 1. Verify order
    # --------------------------------------------------------

    order_result = get_order_details.invoke(
        {"order_id": str(order_id)}
    )

    if not order_result.get("success"):
        return _failure(
            order_result.get(
                "message",
                f"Order {order_id} could not be found during "
                "refund validation.",
            )
        )

    # --------------------------------------------------------
    # 2. Verify payment
    # --------------------------------------------------------

    payment_result = get_payment_details.invoke(
        {"order_id": str(order_id)}
    )

    if not payment_result.get("success"):
        return _failure(
            "Payment information could not be verified "
            "during refund validation."
        )

    payment = payment_result.get("payment", {})

    payment_status = str(
        payment.get("payment_status", "")
    ).upper()

    if payment_status != "SUCCESS":
        return _failure(
            f"Payment for order {order_id} is not successful."
        )

    # --------------------------------------------------------
    # 3. Look for existing refund
    # --------------------------------------------------------

    refund_result = get_refund_details.invoke(
        {"order_id": str(order_id)}
    )

    refund_exists = refund_result.get(
        "refund_exists",
        False,
    )

    refund = (
        refund_result.get("refund", {})
        if refund_exists
        else {}
    )

    current_strategy = str(
        state.get("current_strategy", "")
    ).upper()

    # --------------------------------------------------------
    # 4. Pre-action eligibility
    # --------------------------------------------------------

    if not refund_exists:

        if current_strategy == "REFUND_ELIGIBILITY_REVIEW":

            return {
                "resolution_success": False,
                "action_ready": True,
                "resolution_result": {
                    "operation": "REFUND_ELIGIBILITY_VALIDATED",
                    "order_id": order_id,
                    "payment_status": payment_status,
                    "refund_exists": False,
                    "eligible_for_action": True,
                },
                "resolution_failure_reason": "",
                "status": "ACTION_READY",
            }

        return _failure(
            "No refund record exists after the resolution attempt."
        )

    # --------------------------------------------------------
    # 5. Existing refund
    # --------------------------------------------------------

    refund_status = str(
        refund.get("refund_status", "")
    ).upper()

    refund_id = refund.get(
        "refund_id",
        "",
    )

    customer_waiting = _customer_waiting_for_refund(
        state
    )

    # --------------------------------------------------------
    # 6. Customer waiting for existing refund
    # --------------------------------------------------------

    if customer_waiting:

        if refund_status != "COMPLETED":

            return _failure(
                f"Refund {refund_id} is currently "
                f"{refund_status}. "
                "The customer's refund has not yet reached "
                "a resolved state."
            )

    # --------------------------------------------------------
    # 7. Customer requesting a new refund
    # --------------------------------------------------------

    else:

        if refund_status not in {
            "PROCESSING",
            "COMPLETED",
        }:

            return _failure(
                f"Refund {refund_id} is currently "
                f"{refund_status}. "
                "The refund has not reached a resolved state."
            )

    # --------------------------------------------------------
    # 8. Refund successfully validated
    # --------------------------------------------------------

    return _success(
        {
            "operation": "REFUND_VALIDATED",
            "order_id": order_id,
            "refund_id": refund_id,
            "refund_status": refund_status,
            "amount": float(
                refund.get("refund_amount", 0) or 0
            ),
        }
    )


# ============================================================
# RETURN VALIDATION
# ============================================================

def _validate_return(
    state: dict[str, Any],
) -> dict[str, Any]:

    order_id = state.get("order_id")

    if not order_id:
        return _failure(
            "Order ID is required to validate the return."
        )

    result = get_return_details.invoke(
        {"order_id": str(order_id)}
    )

    if not result.get("success"):
        return _failure(
            result.get(
                "message",
                f"Return information for order {order_id} "
                "could not be retrieved.",
            )
        )

    if not result.get("return_exists"):
        return _failure(
            f"No return record exists for order {order_id}."
        )

    return_record = result.get(
        "return",
        {},
    )

    return _success(
        {
            "operation": "RETURN_INFORMATION_VALIDATED",
            "order_id": order_id,
            "return_id": return_record.get(
                "return_id",
                "",
            ),
            "return_status": return_record.get(
                "return_status",
                "",
            ),
            "return_reason": return_record.get(
                "return_reason",
                "",
            ),
        }
    )


# ============================================================
# CANCELLATION VALIDATION
# ============================================================

def _validate_cancellation(
    state: dict[str, Any],
) -> dict[str, Any]:

    order_id = state.get("order_id")

    if not order_id:
        return _failure(
            "Order ID is required to validate cancellation."
        )

    result = get_order_details.invoke(
        {"order_id": str(order_id)}
    )

    if not result.get("success"):
        return _failure(
            result.get(
                "message",
                f"Order {order_id} could not be found.",
            )
        )

    order = result.get("order", {})

    order_status = str(
        order.get("order_status", "")
    ).upper()

    return _success(
        {
            "operation": "CANCELLATION_STATUS_VALIDATED",
            "order_id": order_id,
            "order_status": order_status,
        }
    )


# ============================================================
# PRODUCT QUERY VALIDATION
# ============================================================

def _validate_product_query(
    state: dict[str, Any],
) -> dict[str, Any]:

    product_id = state.get("product_id")

    if not product_id:

        order_id = state.get("order_id")

        if not order_id:
            return _failure(
                "Product ID is required to validate the "
                "product information."
            )

        order_result = get_order_details.invoke(
            {"order_id": str(order_id)}
        )

        if not order_result.get("success"):
            return _failure(
                "Product information could not be determined "
                "from the order."
            )

        product_id = order_result.get(
            "order",
            {},
        ).get("product_id")

    if not product_id:
        return _failure(
            "Product ID could not be determined."
        )

    result = get_product_details.invoke(
        {"product_id": str(product_id)}
    )

    if not result.get("success"):
        return _failure(
            result.get(
                "message",
                f"Product {product_id} could not be found.",
            )
        )

    product = result.get("product", {})

    return _success(
        {
            "operation": "PRODUCT_INFORMATION_VALIDATED",
            "product_id": product.get(
                "product_id",
                product_id,
            ),
            "product_name": product.get(
                "product_name",
                "",
            ),
            "category": product.get(
                "category",
                "",
            ),
            "brand": product.get(
                "brand",
                "",
            ),
            "return_eligible": product.get(
                "return_eligible",
                False,
            ),
        }
    )


# ============================================================
# MAIN VALIDATION ENTRY POINT
# ============================================================

def validate_resolution(
    state: dict[str, Any],
) -> dict[str, Any]:

    domain = str(
        state.get("domain")
        or state.get("issue_type")
        or ""
    ).upper()

    # --------------------------------------------------------
    # Respect explicit strategy failure
    # --------------------------------------------------------

    resolution_result = state.get(
        "resolution_result",
        {},
    )

    if (
        isinstance(resolution_result, dict)
        and resolution_result.get("success") is False
    ):
        return _failure(
            resolution_result.get(
                "message",
                resolution_result.get(
                    "error_code",
                    "The resolution strategy failed.",
                ),
            )
        )

    # --------------------------------------------------------
    # Respect action failure
    # --------------------------------------------------------

    action_result = state.get(
        "action_result",
        {},
    )

    if (
        isinstance(action_result, dict)
        and action_result
        and not action_result.get("success", False)
    ):
        return _failure(
            action_result.get(
                "message",
                action_result.get(
                    "error_code",
                    "The action failed.",
                ),
            )
        )

    # --------------------------------------------------------
    # Select validator
    # --------------------------------------------------------

    validators = {
        "ORDER": _validate_order,
        "PAYMENT": _validate_payment,
        "DELIVERY": _validate_delivery,
        "REFUND": _validate_refund,
        "RETURN": _validate_return,
        "CANCELLATION": _validate_cancellation,
        "PRODUCT_QUERY": _validate_product_query,
    }

    validator = validators.get(domain)

    if not validator:
        return _failure(
            f"No validation logic is defined for domain '{domain}'."
        )

    return validator(state)