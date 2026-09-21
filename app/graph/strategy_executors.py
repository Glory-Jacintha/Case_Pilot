from __future__ import annotations

from typing import Any, Callable

from app.tools.read_tools import (
    get_delivery_details,
    get_order_details,
    get_payment_details,
    get_product_details,
    get_refund_details,
    get_return_details,
)


def _order_id_required(state: dict) -> tuple[str | None, dict | None]:
    order_id = state.get("order_id")

    if not order_id:
        return None, {
            "success": False,
            "error_code": "ORDER_ID_MISSING",
            "message": "Order ID is required.",
        }

    return str(order_id), None


# =========================================================
# ORDER
# =========================================================

def execute_order_status_check(state: dict) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    return get_order_details.invoke({"order_id": order_id})


def execute_order_details_review(state: dict) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    result = get_order_details.invoke({"order_id": order_id})

    if not result.get("success"):
        return result

    return {
        "success": True,
        "message": "Order details were successfully retrieved.",
        "order": result.get("order"),
    }


def execute_order_status_recheck(state: dict) -> dict[str, Any]:
    return execute_order_status_check(state)


# =========================================================
# PAYMENT
# =========================================================

def execute_payment_status_check(state: dict) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    return get_payment_details.invoke({"order_id": order_id})


def execute_payment_reconciliation(state: dict) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    payment = get_payment_details.invoke({"order_id": order_id})
    order = get_order_details.invoke({"order_id": order_id})

    if not payment.get("success"):
        return payment

    if not order.get("success"):
        return order

    return {
        "success": True,
        "message": (
            "Payment and order records were retrieved "
            "for reconciliation."
        ),
        "payment": payment.get("payment"),
        "order": order.get("order"),
        "operation": "PAYMENT_RECONCILIATION",
    }


def execute_payment_reference_review(state: dict) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    result = get_payment_details.invoke({"order_id": order_id})

    if not result.get("success"):
        return result

    payment = result.get("payment", {})

    return {
        "success": True,
        "message": "Payment gateway reference was reviewed.",
        "transaction_id": payment.get("transaction_id"),
        "gateway_reference": payment.get("gateway_reference"),
        "payment_status": payment.get("payment_status"),
        "payment": payment,
    }


# =========================================================
# DELIVERY
# =========================================================

def execute_delivery_tracking_recheck(state: dict) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    return get_delivery_details.invoke({"order_id": order_id})


def execute_delivery_proof_review(state: dict) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    result = get_delivery_details.invoke({"order_id": order_id})

    if not result.get("success"):
        return result

    delivery = result.get("delivery", {})

    return {
        "success": True,
        "message": "Delivery proof and delivery attempts were reviewed.",
        "delivery_status": delivery.get("delivery_status"),
        "delivery_proof": delivery.get("delivery_proof"),
        "delivery_attempts": delivery.get("delivery_attempts"),
        "delivery": delivery,
    }


def execute_delivery_exception_review(state: dict) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    result = get_delivery_details.invoke({"order_id": order_id})

    if not result.get("success"):
        return result

    return {
        "success": True,
        "message": "Delivery exception evidence was reviewed.",
        "delivery": result.get("delivery"),
        "operation": "DELIVERY_EXCEPTION_REVIEW",
    }


# =========================================================
# REFUND
# =========================================================

def execute_refund_status_check(state: dict) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    return get_refund_details.invoke({"order_id": order_id})


def execute_refund_transaction_reconciliation(
    state: dict,
) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    refund = get_refund_details.invoke({"order_id": order_id})
    payment = get_payment_details.invoke({"order_id": order_id})

    if not refund.get("success"):
        return refund

    if not payment.get("success"):
        return payment

    return {
        "success": True,
        "message": (
            "Refund and payment records were retrieved "
            "for reconciliation."
        ),
        "refund": refund.get("refund"),
        "payment": payment.get("payment"),
        "operation": "REFUND_TRANSACTION_RECONCILIATION",
    }


def execute_refund_eligibility_review(
    state: dict,
) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    order = get_order_details.invoke({"order_id": order_id})

    if not order.get("success"):
        return order

    return {
        "success": True,
        "message": (
            "Order information was retrieved for "
            "refund eligibility review."
        ),
        "order": order.get("order"),
        "operation": "REFUND_ELIGIBILITY_REVIEW",
    }


# =========================================================
# RETURN
# =========================================================

def execute_return_eligibility_check(
    state: dict,
) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    order = get_order_details.invoke({"order_id": order_id})

    if not order.get("success"):
        return order

    order_data = order.get("order", {})
    product_id = order_data.get("product_id")

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
        {"product_id": product_id}
    )

    if not product.get("success"):
        return product

    return {
        "success": True,
        "message": (
            "Order and product information were retrieved "
            "for return eligibility review."
        ),
        "order": order_data,
        "product": product.get("product"),
        "operation": "RETURN_ELIGIBILITY_CHECK",
    }


def execute_return_status_check(state: dict) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    return get_return_details.invoke({"order_id": order_id})


def execute_return_policy_review(
    state: dict,
) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    order = get_order_details.invoke({"order_id": order_id})

    if not order.get("success"):
        return order

    order_data = order.get("order", {})
    product_id = order_data.get("product_id")

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
        {"product_id": product_id}
    )

    if not product.get("success"):
        return product

    return {
        "success": True,
        "message": "Product return-policy information was retrieved.",
        "product": product.get("product"),
        "operation": "RETURN_POLICY_REVIEW",
    }


# =========================================================
# CANCELLATION
# =========================================================

def execute_cancellation_eligibility_check(
    state: dict,
) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    return get_order_details.invoke({"order_id": order_id})


def execute_order_state_review(
    state: dict,
) -> dict[str, Any]:
    order_id, error = _order_id_required(state)

    if error:
        return error

    result = get_order_details.invoke({"order_id": order_id})

    if not result.get("success"):
        return result

    order = result.get("order", {})

    return {
        "success": True,
        "message": "Current order state was reviewed.",
        "order_status": order.get("order_status"),
        "order": order,
        "operation": "ORDER_STATE_REVIEW",
    }


def execute_cancellation_status_recheck(
    state: dict,
) -> dict[str, Any]:
    return execute_cancellation_eligibility_check(state)


# =========================================================
# PRODUCT QUERY
# =========================================================

def execute_product_details_check(
    state: dict,
) -> dict[str, Any]:

    product_id = state.get("product_id")

    if not product_id:
        order_id = state.get("order_id")

        if not order_id:
            return {
                "success": False,
                "error_code": "PRODUCT_ID_MISSING",
                "message": "Product ID is required.",
            }

        order = get_order_details.invoke(
            {"order_id": str(order_id)}
        )

        if not order.get("success"):
            return order

        product_id = order.get("order", {}).get("product_id")

    return get_product_details.invoke(
        {"product_id": str(product_id)}
    )


def execute_product_policy_review(
    state: dict,
) -> dict[str, Any]:
    return execute_product_details_check(state)


def execute_product_information_recheck(
    state: dict,
) -> dict[str, Any]:
    return execute_product_details_check(state)


# =========================================================
# REGISTRY
# =========================================================

STRATEGY_EXECUTORS: dict[
    str,
    Callable[[dict], dict[str, Any]]
] = {
    "ORDER_STATUS_CHECK": execute_order_status_check,
    "ORDER_DETAILS_REVIEW": execute_order_details_review,
    "ORDER_STATUS_RECHECK": execute_order_status_recheck,

    "PAYMENT_STATUS_CHECK": execute_payment_status_check,
    "PAYMENT_RECONCILIATION": execute_payment_reconciliation,
    "PAYMENT_REFERENCE_REVIEW": execute_payment_reference_review,

    "DELIVERY_TRACKING_RECHECK": execute_delivery_tracking_recheck,
    "DELIVERY_PROOF_REVIEW": execute_delivery_proof_review,
    "DELIVERY_EXCEPTION_REVIEW": execute_delivery_exception_review,

    "REFUND_STATUS_CHECK": execute_refund_status_check,
    "REFUND_TRANSACTION_RECONCILIATION":
        execute_refund_transaction_reconciliation,
    "REFUND_ELIGIBILITY_REVIEW":
        execute_refund_eligibility_review,

    "RETURN_ELIGIBILITY_CHECK":
        execute_return_eligibility_check,
    "RETURN_STATUS_CHECK":
        execute_return_status_check,
    "RETURN_POLICY_REVIEW":
        execute_return_policy_review,

    "CANCELLATION_ELIGIBILITY_CHECK":
        execute_cancellation_eligibility_check,
    "ORDER_STATE_REVIEW":
        execute_order_state_review,
    "CANCELLATION_STATUS_RECHECK":
        execute_cancellation_status_recheck,

    "PRODUCT_DETAILS_CHECK":
        execute_product_details_check,
    "PRODUCT_POLICY_REVIEW":
        execute_product_policy_review,
    "PRODUCT_INFORMATION_RECHECK":
        execute_product_information_recheck,
}


def execute_strategy(
    strategy_name: str,
    state: dict,
) -> dict[str, Any]:
    """
    Execute a registered strategy by name.
    """

    executor = STRATEGY_EXECUTORS.get(strategy_name)

    if executor is None:
        return {
            "success": False,
            "error_code": "STRATEGY_NOT_REGISTERED",
            "message": (
                f"No executor is registered for strategy "
                f"'{strategy_name}'."
            ),
        }

    try:
        return executor(state)

    except Exception as exc:
        return {
            "success": False,
            "error_code": "STRATEGY_EXECUTION_ERROR",
            "message": str(exc),
        }