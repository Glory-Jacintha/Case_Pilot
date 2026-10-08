from __future__ import annotations

from typing import Any, Callable, TypedDict

from app.tools.read_tools import (
    get_delivery_details,
    get_order_details,
    get_payment_details,
    get_product_details,
    get_refund_details,
    get_return_details,
)


# ============================================================
# STRATEGY DEFINITION
# ============================================================


class StrategyDefinition(TypedDict, total=False):
    """
    Definition of one autonomous resolution strategy.

    Strategies are read/investigation steps.

    They must NOT perform financial/write transactions.
    """

    name: str
    description: str
    purpose: str

    # Optional action that may become possible after
    # this strategy has gathered sufficient evidence.
    action: str

    # Optional domain required to gather additional evidence.
    next_domain: str


# ============================================================
# STRATEGIES BY DOMAIN
# ============================================================


DOMAIN_STRATEGIES: dict[
    str,
    list[StrategyDefinition],
] = {

    # ========================================================
    # ORDER
    # ========================================================

    "ORDER": [

        {
            "name": "ORDER_STATUS_CHECK",
            "description": (
                "Check the current order status and order details."
            ),
            "purpose": (
                "Establish the current state of the customer's order."
            ),
        },

        {
            "name": "ORDER_DETAILS_REVIEW",
            "description": (
                "Review order items, quantity, amount, "
                "and customer/order information."
            ),
            "purpose": (
                "Gather exact order information needed "
                "for downstream decisions."
            ),
        },

        {
            "name": "ORDER_STATUS_RECHECK",
            "description": (
                "Re-check the order state when the first "
                "investigation is inconclusive."
            ),
            "purpose": (
                "Confirm the latest order state before "
                "re-planning the case."
            ),
        },
    ],


    # ========================================================
    # PAYMENT
    # ========================================================

    "PAYMENT": [

        {
            "name": "PAYMENT_STATUS_CHECK",
            "description": (
                "Check the payment transaction status."
            ),
            "purpose": (
                "Determine whether the payment succeeded, "
                "failed, remained pending, or was reversed."
            ),
        },

        {
            "name": "PAYMENT_RECONCILIATION",
            "description": (
                "Compare the payment transaction "
                "with the associated order."
            ),
            "purpose": (
                "Determine whether the payment and order "
                "records are consistent."
            ),
        },

        {
            "name": "PAYMENT_REFERENCE_REVIEW",
            "description": (
                "Review the payment gateway reference "
                "and transaction evidence."
            ),
            "purpose": (
                "Gather transaction-level evidence when "
                "payment status alone is insufficient."
            ),
        },
    ],


    # ========================================================
    # DELIVERY
    # ========================================================

    "DELIVERY": [

        {
            "name": "DELIVERY_TRACKING_RECHECK",
            "description": (
                "Re-check shipment tracking and delivery status."
            ),
            "purpose": (
                "Determine the latest known shipment state."
            ),
        },

        {
            "name": "DELIVERY_PROOF_REVIEW",
            "description": (
                "Review available delivery proof "
                "and delivery attempts."
            ),
            "purpose": (
                "Determine whether there is evidence that "
                "the order was delivered or delivery was attempted."
            ),
        },

        {
            "name": "DELIVERY_EXCEPTION_REVIEW",
            "description": (
                "Review delivery evidence for missing, "
                "delayed, or disputed delivery."
            ),
            "purpose": (
                "Determine whether the case requires "
                "another domain such as RETURN or REFUND."
            ),
        },
    ],


    # ========================================================
    # REFUND
    # ========================================================

    "REFUND": [

        {
            "name": "REFUND_STATUS_CHECK",
            "description": (
                "Check the current refund status and refund record."
            ),
            "purpose": (
                "Determine whether a refund already exists "
                "and its current state."
            ),
        },

        {
            "name": "REFUND_TRANSACTION_RECONCILIATION",
            "description": (
                "Reconcile the refund with the original "
                "payment transaction."
            ),
            "purpose": (
                "Determine whether the refund is consistent "
                "with the original payment."
            ),
            "next_domain": "PAYMENT",
        },

        {
            "name": "REFUND_ELIGIBILITY_REVIEW",
            "description": (
                "Review refund eligibility using product, "
                "order, and policy information."
            ),
            "purpose": (
                "Determine whether the customer is eligible "
                "for a refund before a financial action."
            ),
            "action": "CREATE_REFUND",
        },
    ],


    # ========================================================
    # RETURN
    # ========================================================

    "RETURN": [

        {
            "name": "RETURN_ELIGIBILITY_CHECK",
            "description": (
                "Check whether the product and order "
                "are eligible for return."
            ),
            "purpose": (
                "Determine whether the requested return "
                "is allowed."
            ),
        },

        {
            "name": "RETURN_STATUS_CHECK",
            "description": (
                "Check the current return status."
            ),
            "purpose": (
                "Determine whether a return already exists "
                "and its current state."
            ),
        },

        {
            "name": "RETURN_POLICY_REVIEW",
            "description": (
                "Review the applicable return window "
                "and product policy."
            ),
            "purpose": (
                "Determine whether the requested return "
                "satisfies the applicable policy."
            ),
        },
    ],


    # ========================================================
    # CANCELLATION
    # ========================================================

    "CANCELLATION": [

        {
            "name": "CANCELLATION_ELIGIBILITY_CHECK",
            "description": (
                "Check whether the order can currently "
                "be cancelled."
            ),
            "purpose": (
                "Determine whether cancellation is possible "
                "from the current order state."
            ),
        },

        {
            "name": "ORDER_STATE_REVIEW",
            "description": (
                "Review the current order state to determine "
                "cancellation feasibility."
            ),
            "purpose": (
                "Use the latest order state as evidence "
                "for cancellation."
            ),
        },

        {
            "name": "CANCELLATION_STATUS_RECHECK",
            "description": (
                "Re-check cancellation-related order information."
            ),
            "purpose": (
                "Confirm the latest order state before "
                "attempting a cancellation action."
            ),
        },
    ],


    # ========================================================
    # PRODUCT QUERY
    # ========================================================

    "PRODUCT_QUERY": [

        {
            "name": "PRODUCT_DETAILS_CHECK",
            "description": (
                "Retrieve the product's available information "
                "and characteristics."
            ),
            "purpose": (
                "Answer product-related questions using "
                "database-grounded product information."
            ),
        },

        {
            "name": "PRODUCT_POLICY_REVIEW",
            "description": (
                "Review relevant product-related policy information."
            ),
            "purpose": (
                "Determine applicable product policy information "
                "before answering."
            ),
        },

        {
            "name": "PRODUCT_INFORMATION_RECHECK",
            "description": (
                "Re-check product information when the first "
                "investigation is incomplete."
            ),
            "purpose": (
                "Confirm product information before responding."
            ),
        },
    ],
}


# ============================================================
# STRATEGY REGISTRY
# ============================================================


def get_strategies_for_domain(
    domain: str,
) -> list[StrategyDefinition]:
    """
    Return the strategies registered for the selected
    CasePilot support domain.
    """

    normalized_domain = str(
        domain or ""
    ).upper().strip()

    if normalized_domain not in DOMAIN_STRATEGIES:

        raise ValueError(
            f"Unsupported CasePilot domain: "
            f"{normalized_domain}"
        )

    return DOMAIN_STRATEGIES[
        normalized_domain
    ]


# ============================================================
# COMMON HELPERS
# ============================================================


def _order_id_required(
    state: dict,
) -> tuple[str | None, dict | None]:
    """
    Validate that an order ID exists.
    """

    order_id = state.get(
        "order_id"
    )

    if not order_id:

        return None, {
            "success": False,
            "error_code": "ORDER_ID_MISSING",
            "message": (
                "Order ID is required."
            ),
        }

    return (
        str(order_id),
        None,
    )


def _product_id_required(
    state: dict,
) -> tuple[str | None, dict | None]:
    """
    Validate that a product ID exists.
    """

    product_id = state.get(
        "product_id"
    )

    if not product_id:

        return None, {
            "success": False,
            "error_code": "PRODUCT_ID_MISSING",
            "message": (
                "Product ID is required."
            ),
        }

    return (
        str(product_id),
        None,
    )


# ============================================================
# ORDER STRATEGIES
# ============================================================


def execute_order_status_check(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    return get_order_details.invoke(
        {
            "order_id": order_id,
        }
    )


def execute_order_details_review(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    result = get_order_details.invoke(
        {
            "order_id": order_id,
        }
    )

    if not result.get(
        "success",
        False,
    ):
        return result

    return {
        "success": True,
        "message": (
            "Order details were successfully retrieved."
        ),
        "order": result.get(
            "order"
        ),
        "operation": (
            "ORDER_DETAILS_REVIEW"
        ),
    }


def execute_order_status_recheck(
    state: dict,
) -> dict[str, Any]:

    return execute_order_status_check(
        state
    )


# ============================================================
# PAYMENT STRATEGIES
# ============================================================


def execute_payment_status_check(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    return get_payment_details.invoke(
        {
            "order_id": order_id,
        }
    )


def execute_payment_reconciliation(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    payment = get_payment_details.invoke(
        {
            "order_id": order_id,
        }
    )

    order = get_order_details.invoke(
        {
            "order_id": order_id,
        }
    )

    if not payment.get(
        "success",
        False,
    ):
        return payment

    if not order.get(
        "success",
        False,
    ):
        return order

    return {
        "success": True,
        "message": (
            "Payment and order records were retrieved "
            "for reconciliation."
        ),
        "payment": payment.get(
            "payment"
        ),
        "order": order.get(
            "order"
        ),
        "operation": (
            "PAYMENT_RECONCILIATION"
        ),
    }


def execute_payment_reference_review(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    result = get_payment_details.invoke(
        {
            "order_id": order_id,
        }
    )

    if not result.get(
        "success",
        False,
    ):
        return result

    payment = result.get(
        "payment",
        {},
    )

    return {
        "success": True,
        "message": (
            "Payment gateway reference was reviewed."
        ),
        "transaction_id": payment.get(
            "transaction_id"
        ),
        "gateway_reference": payment.get(
            "gateway_reference"
        ),
        "payment_status": payment.get(
            "payment_status"
        ),
        "payment": payment,
        "operation": (
            "PAYMENT_REFERENCE_REVIEW"
        ),
    }


# ============================================================
# DELIVERY STRATEGIES
# ============================================================


def execute_delivery_tracking_recheck(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    return get_delivery_details.invoke(
        {
            "order_id": order_id,
        }
    )


def execute_delivery_proof_review(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    result = get_delivery_details.invoke(
        {
            "order_id": order_id,
        }
    )

    if not result.get(
        "success",
        False,
    ):
        return result

    delivery = result.get(
        "delivery",
        {},
    )

    return {
        "success": True,
        "message": (
            "Delivery proof and delivery attempts "
            "were reviewed."
        ),
        "delivery_status": delivery.get(
            "delivery_status"
        ),
        "delivery_proof": delivery.get(
            "delivery_proof"
        ),
        "delivery_attempts": delivery.get(
            "delivery_attempts"
        ),
        "delivery": delivery,
        "operation": (
            "DELIVERY_PROOF_REVIEW"
        ),
    }


def execute_delivery_exception_review(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    result = get_delivery_details.invoke(
        {
            "order_id": order_id,
        }
    )

    if not result.get(
        "success",
        False,
    ):
        return result

    return {
        "success": True,
        "message": (
            "Delivery exception evidence was reviewed."
        ),
        "delivery": result.get(
            "delivery"
        ),
        "operation": (
            "DELIVERY_EXCEPTION_REVIEW"
        ),
    }


# ============================================================
# REFUND STRATEGIES
# ============================================================


def execute_refund_status_check(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    return get_refund_details.invoke(
        {
            "order_id": order_id,
        }
    )


def execute_refund_transaction_reconciliation(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    refund = get_refund_details.invoke(
        {
            "order_id": order_id,
        }
    )

    payment = get_payment_details.invoke(
        {
            "order_id": order_id,
        }
    )

    if not refund.get(
        "success",
        False,
    ):
        return refund

    if not payment.get(
        "success",
        False,
    ):
        return payment

    return {
        "success": True,
        "message": (
            "Refund and payment records were retrieved "
            "for reconciliation."
        ),
        "refund": refund.get(
            "refund"
        ),
        "payment": payment.get(
            "payment"
        ),
        "operation": (
            "REFUND_TRANSACTION_RECONCILIATION"
        ),
    }


def execute_refund_eligibility_review(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    order = get_order_details.invoke(
        {
            "order_id": order_id,
        }
    )

    if not order.get(
        "success",
        False,
    ):
        return order

    order_data = order.get(
        "order",
        {},
    )

    return {
        "success": True,
        "message": (
            "Order information was retrieved for "
            "refund eligibility review."
        ),
        "order": order_data,
        "operation": (
            "REFUND_ELIGIBILITY_REVIEW"
        ),
        "action_candidate": (
            "CREATE_REFUND"
        ),
    }


# ============================================================
# RETURN STRATEGIES
# ============================================================


def execute_return_eligibility_check(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    order = get_order_details.invoke(
        {
            "order_id": order_id,
        }
    )

    if not order.get(
        "success",
        False,
    ):
        return order

    order_data = order.get(
        "order",
        {},
    )

    product_id = order_data.get(
        "product_id"
    )

    if not product_id:

        return {
            "success": False,
            "error_code": "PRODUCT_ID_MISSING",
            "message": (
                "Product ID could not be determined "
                "from the order."
            ),
        }

    product = get_product_details.invoke(
        {
            "product_id": str(
                product_id
            ),
        }
    )

    if not product.get(
        "success",
        False,
    ):
        return product

    return {
        "success": True,
        "message": (
            "Order and product information were retrieved "
            "for return eligibility review."
        ),
        "order": order_data,
        "product": product.get(
            "product"
        ),
        "operation": (
            "RETURN_ELIGIBILITY_CHECK"
        ),
    }


def execute_return_status_check(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    return get_return_details.invoke(
        {
            "order_id": order_id,
        }
    )


def execute_return_policy_review(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    order = get_order_details.invoke(
        {
            "order_id": order_id,
        }
    )

    if not order.get(
        "success",
        False,
    ):
        return order

    order_data = order.get(
        "order",
        {},
    )

    product_id = order_data.get(
        "product_id"
    )

    if not product_id:

        return {
            "success": False,
            "error_code": "PRODUCT_ID_MISSING",
            "message": (
                "Product ID could not be determined "
                "from the order."
            ),
        }

    product = get_product_details.invoke(
        {
            "product_id": str(
                product_id
            ),
        }
    )

    if not product.get(
        "success",
        False,
    ):
        return product

    return {
        "success": True,
        "message": (
            "Product return-policy information "
            "was retrieved."
        ),
        "product": product.get(
            "product"
        ),
        "operation": (
            "RETURN_POLICY_REVIEW"
        ),
    }


# ============================================================
# CANCELLATION STRATEGIES
# ============================================================


def execute_cancellation_eligibility_check(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    return get_order_details.invoke(
        {
            "order_id": order_id,
        }
    )


def execute_order_state_review(
    state: dict,
) -> dict[str, Any]:

    order_id, error = _order_id_required(
        state
    )

    if error:
        return error

    result = get_order_details.invoke(
        {
            "order_id": order_id,
        }
    )

    if not result.get(
        "success",
        False,
    ):
        return result

    order = result.get(
        "order",
        {},
    )

    return {
        "success": True,
        "message": (
            "Current order state was reviewed."
        ),
        "order_status": order.get(
            "order_status"
        ),
        "order": order,
        "operation": (
            "ORDER_STATE_REVIEW"
        ),
    }


def execute_cancellation_status_recheck(
    state: dict,
) -> dict[str, Any]:

    return execute_cancellation_eligibility_check(
        state
    )


# ============================================================
# PRODUCT QUERY STRATEGIES
# ============================================================


def execute_product_details_check(
    state: dict,
) -> dict[str, Any]:

    product_id = state.get(
        "product_id"
    )

    # --------------------------------------------------------
    # Resolve product ID from order when possible
    # --------------------------------------------------------

    if not product_id:

        order_id = state.get(
            "order_id"
        )

        if not order_id:

            return {
                "success": False,
                "error_code": "PRODUCT_ID_MISSING",
                "message": (
                    "Product ID is required."
                ),
            }

        order = get_order_details.invoke(
            {
                "order_id": str(
                    order_id
                ),
            }
        )

        if not order.get(
            "success",
            False,
        ):
            return order

        product_id = order.get(
            "order",
            {},
        ).get(
            "product_id"
        )

    if not product_id:

        return {
            "success": False,
            "error_code": "PRODUCT_ID_MISSING",
            "message": (
                "Product ID could not be determined."
            ),
        }

    return get_product_details.invoke(
        {
            "product_id": str(
                product_id
            ),
        }
    )


def execute_product_policy_review(
    state: dict,
) -> dict[str, Any]:

    return execute_product_details_check(
        state
    )


def execute_product_information_recheck(
    state: dict,
) -> dict[str, Any]:

    return execute_product_details_check(
        state
    )


# ============================================================
# EXECUTOR REGISTRY
# ============================================================


STRATEGY_EXECUTORS: dict[
    str,
    Callable[[dict], dict[str, Any]],
] = {

    # --------------------------------------------------------
    # ORDER
    # --------------------------------------------------------

    "ORDER_STATUS_CHECK":
        execute_order_status_check,

    "ORDER_DETAILS_REVIEW":
        execute_order_details_review,

    "ORDER_STATUS_RECHECK":
        execute_order_status_recheck,

    # --------------------------------------------------------
    # PAYMENT
    # --------------------------------------------------------

    "PAYMENT_STATUS_CHECK":
        execute_payment_status_check,

    "PAYMENT_RECONCILIATION":
        execute_payment_reconciliation,

    "PAYMENT_REFERENCE_REVIEW":
        execute_payment_reference_review,

    # --------------------------------------------------------
    # DELIVERY
    # --------------------------------------------------------

    "DELIVERY_TRACKING_RECHECK":
        execute_delivery_tracking_recheck,

    "DELIVERY_PROOF_REVIEW":
        execute_delivery_proof_review,

    "DELIVERY_EXCEPTION_REVIEW":
        execute_delivery_exception_review,

    # --------------------------------------------------------
    # REFUND
    # --------------------------------------------------------

    "REFUND_STATUS_CHECK":
        execute_refund_status_check,

    "REFUND_TRANSACTION_RECONCILIATION":
        execute_refund_transaction_reconciliation,

    "REFUND_ELIGIBILITY_REVIEW":
        execute_refund_eligibility_review,

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    "RETURN_ELIGIBILITY_CHECK":
        execute_return_eligibility_check,

    "RETURN_STATUS_CHECK":
        execute_return_status_check,

    "RETURN_POLICY_REVIEW":
        execute_return_policy_review,

    # --------------------------------------------------------
    # CANCELLATION
    # --------------------------------------------------------

    "CANCELLATION_ELIGIBILITY_CHECK":
        execute_cancellation_eligibility_check,

    "ORDER_STATE_REVIEW":
        execute_order_state_review,

    "CANCELLATION_STATUS_RECHECK":
        execute_cancellation_status_recheck,

    # --------------------------------------------------------
    # PRODUCT
    # --------------------------------------------------------

    "PRODUCT_DETAILS_CHECK":
        execute_product_details_check,

    "PRODUCT_POLICY_REVIEW":
        execute_product_policy_review,

    "PRODUCT_INFORMATION_RECHECK":
        execute_product_information_recheck,
}


# ============================================================
# GENERIC STRATEGY EXECUTOR
# ============================================================


def execute_strategy(
    strategy_name: str,
    state: dict,
) -> dict[str, Any]:
    """
    Execute a registered read/investigation strategy.

    This function intentionally does NOT execute financial
    transactions.

    Write operations belong to app.graph.actions.
    """

    normalized_name = str(
        strategy_name or ""
    ).strip()

    executor = STRATEGY_EXECUTORS.get(
        normalized_name
    )

    if executor is None:

        return {
            "success": False,
            "error_code": "STRATEGY_NOT_REGISTERED",
            "message": (
                "No executor is registered for "
                f"strategy '{normalized_name}'."
            ),
        }

    try:

        result = executor(
            state
        )

    except Exception as exc:

        return {
            "success": False,
            "error_code": (
                "STRATEGY_EXECUTION_ERROR"
            ),
            "message": str(
                exc
            ),
        }

    if not isinstance(
        result,
        dict,
    ):

        return {
            "success": False,
            "error_code": (
                "INVALID_STRATEGY_RESULT"
            ),
            "message": (
                f"Strategy '{normalized_name}' "
                "returned an invalid result."
            ),
        }

    # --------------------------------------------------------
    # Add strategy identity without overwriting tool data.
    # --------------------------------------------------------

    return {
        **result,
        "strategy": normalized_name,
    }