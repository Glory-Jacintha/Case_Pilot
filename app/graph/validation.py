from __future__ import annotations

from typing import Any

from app.tools.data_store import (
    find_one,
    orders,
    payments,
    refunds,
    deliveries,
    returns,
    products,
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

    order = find_one(
        orders(),
        "OrderID",
        order_id,
    )

    if not order:
        return _failure(
            f"Order {order_id} could not be found during validation."
        )

    return _success(
        {
            "operation": "ORDER_INFORMATION_VALIDATED",
            "order_id": order_id,
            "order_status": order.get(
                "OrderStatus",
                "",
            ),
            "amount": float(
                order.get(
                    "TotalAmount",
                    0,
                )
                or 0
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

    payment = find_one(
        payments(),
        "OrderID",
        order_id,
    )

    if not payment:
        return _failure(
            f"Payment information for order {order_id} "
            "could not be found."
        )

    return _success(
        {
            "operation": "PAYMENT_INFORMATION_VALIDATED",
            "order_id": order_id,
            "transaction_id": payment.get(
                "TransactionID",
                "",
            ),
            "payment_status": payment.get(
                "PaymentStatus",
                "",
            ),
            "amount": float(
                payment.get(
                    "Amount",
                    0,
                )
                or 0
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

    delivery = find_one(
        deliveries(),
        "OrderID",
        order_id,
    )

    if not delivery:
        return _failure(
            f"Delivery information for order {order_id} "
            "could not be found."
        )

    return _success(
        {
            "operation": "DELIVERY_INFORMATION_VALIDATED",
            "order_id": order_id,
            "delivery_status": delivery.get(
                "DeliveryStatus",
                "",
            ),
            "tracking_id": delivery.get(
                "TrackingID",
                "",
            ),
            "courier": delivery.get(
                "Courier",
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
        state.get(
            "customer_message",
            "",
        )
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

    order = find_one(
        orders(),
        "OrderID",
        order_id,
    )

    if not order:
        return _failure(
            f"Order {order_id} could not be found during "
            "refund validation."
        )

    # --------------------------------------------------------
    # 2. Verify payment
    # --------------------------------------------------------

    payment = find_one(
        payments(),
        "OrderID",
        order_id,
    )

    if not payment:
        return _failure(
            "Payment information could not be verified "
            "during refund validation."
        )

    payment_status = str(
        payment.get(
            "PaymentStatus",
            "",
        )
    ).upper()

    # A refund should only proceed when the original payment
    # was successfully completed.
    if payment_status != "SUCCESS":
        return _failure(
            f"Payment for order {order_id} is not successful."
        )

    # --------------------------------------------------------
    # 3. Look for an existing refund
    # --------------------------------------------------------

    refund = find_one(
        refunds(),
        "OrderID",
        order_id,
    )

    current_strategy = str(
        state.get(
            "current_strategy",
            "",
        )
    ).upper()

    # --------------------------------------------------------
    # 4. PRE-ACTION ELIGIBILITY PHASE
    # --------------------------------------------------------
    #
    # If there is no refund record yet, that does NOT
    # automatically mean the case has failed.
    #
    # Specifically, after REFUND_ELIGIBILITY_REVIEW,
    # the system can determine that the refund is eligible
    # and mark the state as ACTION_READY.
    #
    # The action controller will then create the refund.
    # --------------------------------------------------------

    if not refund:

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
        refund.get(
            "RefundStatus",
            "",
        )
    ).upper()

    customer_waiting = _customer_waiting_for_refund(
        state
    )

    # --------------------------------------------------------
    # 6. Customer is waiting for an already-created refund
    # --------------------------------------------------------
    #
    # PROCESSING is NOT enough here.
    #
    # Example:
    # "I haven't received my refund."
    #
    # If refund is still PROCESSING, the customer's issue
    # has not actually been resolved.
    # --------------------------------------------------------

    if customer_waiting:

        if refund_status != "COMPLETED":

            return _failure(
                f"Refund {refund.get('RefundID', '')} "
                f"is currently {refund_status}. "
                "The customer's refund has not yet reached "
                "a resolved state."
            )

    # --------------------------------------------------------
    # 7. Customer is requesting a new refund
    # --------------------------------------------------------
    #
    # Example:
    # "I want a refund for this order."
    #
    # If the refund action successfully creates a PROCESSING
    # refund, the requested transaction has been initiated.
    # Therefore PROCESSING can be considered resolved for
    # this type of request.
    # --------------------------------------------------------

    else:

        if refund_status not in {
            "PROCESSING",
            "COMPLETED",
        }:

            return _failure(
                f"Refund {refund.get('RefundID', '')} "
                f"is currently {refund_status}. "
                "The refund has not reached a resolved state."
            )

    # --------------------------------------------------------
    # 8. Refund successfully validated
    # --------------------------------------------------------

    return _success(
        {
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

    return_record = find_one(
        returns(),
        "OrderID",
        order_id,
    )

    if not return_record:
        return _failure(
            f"No return record exists for order {order_id}."
        )

    return _success(
        {
            "operation": "RETURN_INFORMATION_VALIDATED",
            "order_id": order_id,
            "return_id": return_record.get(
                "ReturnID",
                "",
            ),
            "return_status": return_record.get(
                "ReturnStatus",
                "",
            ),
            "return_reason": return_record.get(
                "ReturnReason",
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

    order = find_one(
        orders(),
        "OrderID",
        order_id,
    )

    if not order:
        return _failure(
            f"Order {order_id} could not be found."
        )

    order_status = str(
        order.get(
            "OrderStatus",
            "",
        )
    ).upper()

    # Cancellation is currently investigation-only.
    # We validate the actual order state rather than
    # pretending that a cancellation transaction occurred.
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
        return _failure(
            "Product ID is required to validate the "
            "product information."
        )

    product = find_one(
        products(),
        "ProductID",
        product_id,
    )

    if not product:
        return _failure(
            f"Product {product_id} could not be found."
        )

    return _success(
        {
            "operation": "PRODUCT_INFORMATION_VALIDATED",
            "product_id": product_id,
            "product_name": product.get(
                "ProductName",
                "",
            ),
            "category": product.get(
                "Category",
                "",
            ),
            "brand": product.get(
                "Brand",
                "",
            ),
            "return_eligible": product.get(
                "ReturnEligible",
                "",
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
        state.get(
            "domain"
        )
        or state.get(
            "issue_type"
        )
        or ""
    ).upper()

    # --------------------------------------------------------
    # If the resolution strategy itself explicitly failed,
    # validation must respect that failure.
    #
    # Example:
    # {
    #     "resolution_result": {
    #         "success": False,
    #         "error_code": "TRACKING_UNAVAILABLE"
    #     }
    # }
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
    # If an action was attempted and failed, validation must
    # also respect that failure instead of looking at stale
    # investigation data.
    # --------------------------------------------------------

    action_result = state.get(
        "action_result",
        {},
    )

    if (
        isinstance(action_result, dict)
        and action_result
        and not action_result.get(
            "success",
            False,
        )
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
    # Select validator based on domain
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