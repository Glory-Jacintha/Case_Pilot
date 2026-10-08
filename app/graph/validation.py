from __future__ import annotations

from typing import Any

from app.graph.policy import currency_from_country
from app.tools.read_tools import (
    get_delivery_details,
    get_order_details,
    get_payment_details,
    get_product_details,
    get_refund_details,
    get_return_details,
)


def _failure(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "resolution_success": False,
        "case_completed": False,
        "resolution_failure_reason": reason,
        "status": "RESOLUTION_VALIDATION_FAILED",
        **extra,
    }


def _success(result: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "resolution_success": True,
        "case_completed": True,
        "resolution_result": result,
        "resolution_failure_reason": "",
        "status": "CASE_COMPLETED",
        **extra,
    }


def _status(record: dict[str, Any], key: str) -> str:
    return str(record.get(key, "")).upper().strip()


def _customer_waiting_for_refund(state: dict[str, Any]) -> bool:
    text = str(state.get("customer_message", "")).lower()
    return any(x in text for x in (
        "haven't received", "have not received", "not received",
        "didn't receive", "did not receive", "still waiting",
        "waiting for refund", "refund pending", "refund hasn't arrived",
        "refund has not arrived",
    ))


def _validate_information_domain(state: dict[str, Any], domain: str) -> dict[str, Any]:
    order_id = state.get("order_id")
    if domain == "ORDER":
        if not order_id:
            return _failure("Order ID is required to validate the order.")
        result = get_order_details.invoke({"order_id": str(order_id)})
        if not result.get("success"):
            return _failure(result.get("error", "Order could not be verified."))
        order = result.get("order") or {}
        return _success({"operation": "ORDER_INFORMATION_VALIDATED", "order": order}, transaction_currency=currency_from_country(order.get("country")))

    if domain == "PAYMENT":
        if not order_id:
            return _failure("Order ID is required to validate the payment.")
        result = get_payment_details.invoke({"order_id": str(order_id)})
        if not result.get("success"):
            return _failure(result.get("error", "Payment could not be verified."))
        payment = result.get("payment") or {}
        order_result = get_order_details.invoke({"order_id": str(order_id)})
        order = order_result.get("order", {}) if order_result.get("success") else {}
        return _success({"operation": "PAYMENT_INFORMATION_VALIDATED", "payment": payment}, transaction_currency=currency_from_country(order.get("country")))

    if domain == "PRODUCT_QUERY":
        product_id = state.get("product_id")
        if not product_id:
            return _failure("Product ID is required to validate product information.")
        result = get_product_details.invoke({"product_id": str(product_id)})
        if not result.get("success"):
            return _failure(result.get("error", "Product could not be verified."))
        return _success({"operation": "PRODUCT_INFORMATION_VALIDATED", "product": result.get("product")})

    return _failure(f"Unsupported information domain: {domain}")


def _validate_delivery(state: dict[str, Any]) -> dict[str, Any]:
    order_id = state.get("order_id")
    if not order_id:
        return _failure("Order ID is required to validate delivery information.")
    result = get_delivery_details.invoke({"order_id": str(order_id)})
    if not result.get("success"):
        return _failure(result.get("error", "Delivery information could not be verified."))
    delivery = result.get("delivery", {}) or {}
    text = str(state.get("customer_message", "")).lower()
    dispute = any(x in text for x in ("didn't receive", "did not receive", "haven't received", "not received", "missing"))
    delivered = _status(delivery, "delivery_status") in {"DELIVERED", "COMPLETED"}
    if dispute and delivered:
        attempts = [a for a in state.get("resolution_attempts", []) or [] if str(a.get("domain", "")).upper() == "DELIVERY"]
        if len(attempts) < 3:
            return _failure("System evidence shows the package as delivered, but the customer disputes receipt.")
        return _failure("Delivery evidence was reviewed through the available strategies, but the delivery dispute could not be safely resolved.", requires_human=True, status="HUMAN_ESCALATION")
    return _success({"operation": "DELIVERY_INFORMATION_VALIDATED", "delivery": delivery})


def _validate_refund(state: dict[str, Any]) -> dict[str, Any]:
    order_id = state.get("order_id")
    if not order_id:
        return _failure("Order ID is required to validate the refund.")

    order_result = get_order_details.invoke({"order_id": str(order_id)})
    if not order_result.get("success"):
        return _failure(order_result.get("error", "Order could not be verified."))
    order = order_result.get("order", {}) or {}

    payment_result = get_payment_details.invoke({"order_id": str(order_id)})
    if not payment_result.get("success"):
        return _failure("Payment information could not be verified during refund validation.")
    payment = payment_result.get("payment", {}) or {}
    if _status(payment, "payment_status") != "SUCCESS":
        return _failure(f"Payment for order {order_id} is not successful.")

    refund_result = get_refund_details.invoke({"order_id": str(order_id)})
    if not refund_result.get("success"):
        return _failure(refund_result.get("error", "Refund information could not be verified."))

    refund = refund_result.get("refund", {}) if refund_result.get("refund_exists") else None
    current_strategy = str(state.get("current_strategy", "")).upper()

    if refund is None:
        if current_strategy == "REFUND_ELIGIBILITY_REVIEW":
            amount = float(order.get("total_amount", 0) or 0)
            return {
                "resolution_success": False,
                "case_completed": False,
                "action_ready": True,
                "transaction_amount": amount,
                "transaction_currency": currency_from_country(order.get("country")),
                "resolution_result": {
                    "operation": "REFUND_ELIGIBILITY_VALIDATED",
                    "order_id": order_id,
                    "eligible_for_action": True,
                    "verified_amount": amount,
                },
                "resolution_failure_reason": "",
                "status": "ACTION_READY",
            }
        return _failure("No refund record exists after the refund investigation.")

    refund_status = _status(refund, "refund_status")
    amount = float(refund.get("refund_amount", order.get("total_amount", 0)) or 0)
    if _customer_waiting_for_refund(state):
        if refund_status != "COMPLETED":
            return _failure(f"Refund {refund.get('refund_id', '')} is currently {refund_status} and has not reached a resolved state.")
    elif refund_status not in {"PROCESSING", "COMPLETED"}:
        return _failure(f"Refund {refund.get('refund_id', '')} is currently {refund_status}.")

    return _success({
        "operation": "REFUND_VALIDATED",
        "order_id": order_id,
        "refund_id": refund.get("refund_id", ""),
        "refund_status": refund_status,
        "amount": amount,
        "currency": currency_from_country(order.get("country")),
    }, transaction_currency=currency_from_country(order.get("country")))


def _explicit_refund_request(state: dict[str, Any]) -> bool:
    text = str(state.get("customer_message") or "").lower()
    return any(
        phrase in text
        for phrase in ("refund", "money back", "moneyback")
    )


def _explicit_return_request(state: dict[str, Any]) -> bool:
    text = str(state.get("customer_message") or "").lower()
    return any(
        phrase in text
        for phrase in ("return", "send it back")
    )


def _validate_cancellation(state: dict[str, Any]) -> dict[str, Any]:
    order_id = state.get("order_id")
    if not order_id:
        return _failure("Order ID is required to validate cancellation.")

    result = get_order_details.invoke({"order_id": str(order_id)})
    if not result.get("success"):
        return _failure(result.get("error", "Order could not be verified."))

    order = result.get("order", {}) or {}
    status = _status(order, "order_status")
    action_result = state.get("action_result", {}) or {}
    action_was_cancelled = (
        str(state.get("action_type") or "").upper() == "CANCEL_ORDER"
        and action_result.get("success") is True
    )
    wants_refund = _explicit_refund_request(state)

    if status == "CANCELLED":
        if action_was_cancelled or wants_refund:
            amount = float(order.get("total_amount", 0) or 0)
            return {
                "resolution_success": False,
                "case_completed": False,
                "action_ready": False,
                "next_domain": "REFUND",
                "transaction_amount": amount,
                "transaction_currency": currency_from_country(order.get("country")),
                "resolution_result": {
                    "operation": "CANCELLATION_COMPLETE",
                    "order_id": order_id,
                    "order_status": status,
                    "amount": amount,
                },
                "resolution_failure_reason": "",
                "status": "DOMAIN_COMPLETED",
            }
        return _success({
            "operation": "ORDER_ALREADY_CANCELLED",
            "order_id": order_id,
            "order_status": status,
        })

    if status in {"DELIVERED", "RETURNED", "SHIPPED", "OUT_FOR_DELIVERY"}:
        if wants_refund:
            amount = float(order.get("total_amount", 0) or 0)
            next_domain = "REFUND" if status == "RETURNED" else "RETURN"
            return {
                "resolution_success": False,
                "case_completed": False,
                "action_ready": False,
                "next_domain": next_domain,
                "transaction_amount": amount,
                "transaction_currency": currency_from_country(order.get("country")),
                "resolution_result": {
                    "operation": "CANCELLATION_NOT_POSSIBLE_REFUND_REQUESTED",
                    "order_id": order_id,
                    "order_status": status,
                    "next_domain": next_domain,
                    "customer_message": (
                        f"Order {order_id} is already {status.lower()}, so it cannot be cancelled. "
                        f"The refund request will continue through the {next_domain.lower()} step."
                    ),
                },
                "resolution_failure_reason": "",
                "status": "DOMAIN_COMPLETED",
            }

        return _success({
            "operation": "CANCELLATION_NOT_POSSIBLE",
            "order_id": order_id,
            "order_status": status,
            "customer_message": (
                f"Order {order_id} is already {status.lower()} and cannot be cancelled."
            ),
        })

    if str(state.get("current_strategy") or "").upper() in {
        "CANCELLATION_ELIGIBILITY_CHECK",
        "ORDER_STATE_REVIEW",
        "CANCELLATION_STATUS_RECHECK",
    }:
        amount = float(order.get("total_amount", 0) or 0)
        return {
            "resolution_success": False,
            "case_completed": False,
            "action_ready": True,
            "transaction_amount": amount,
            "transaction_currency": currency_from_country(order.get("country")),
            "resolution_result": {
                "operation": "CANCELLATION_ELIGIBILITY_VALIDATED",
                "order_id": order_id,
                "order_status": status,
                "eligible_for_action": True,
            },
            "resolution_failure_reason": "",
            "status": "ACTION_READY",
        }

    return _failure(
        f"Order {order_id} is currently {status}; cancellation eligibility is not yet established."
    )


def _validate_return(state: dict[str, Any]) -> dict[str, Any]:
    order_id = state.get("order_id")
    if not order_id:
        return _failure("Order ID is required to validate the return.")
    result = get_return_details.invoke({"order_id": str(order_id)})
    if not result.get("success"):
        return _failure(result.get("error", "Return information could not be verified."))

    order_result = get_order_details.invoke({"order_id": str(order_id)})
    order = order_result.get("order", {}) if order_result.get("success") else {}
    currency = currency_from_country(order.get("country"))
    amount = float(order.get("total_amount", 0) or 0)
    current_strategy = str(state.get("current_strategy") or "").upper()
    action_result = state.get("action_result", {}) or {}
    return_action_completed = (
        str(state.get("action_type") or "").upper() == "PROCESS_RETURN"
        and action_result.get("success") is True
    )
    wants_refund = _explicit_refund_request(state)

    if not result.get("return_exists"):
        if current_strategy == "RETURN_ELIGIBILITY_CHECK":
            return {
                "resolution_success": False,
                "case_completed": False,
                "action_ready": True,
                "transaction_amount": amount,
                "transaction_currency": currency,
                "resolution_result": {
                    "operation": "RETURN_ELIGIBILITY_VALIDATED",
                    "order_id": order_id,
                    "eligible_for_action": True,
                },
                "resolution_failure_reason": "",
                "status": "ACTION_READY",
            }
        return _failure("No return record exists after the return investigation.")

    ret = result.get("return", {}) or {}
    status = _status(ret, "return_status")
    if status not in {"RECEIVED", "COMPLETED"}:
        return _failure(
            f"Return {ret.get('return_id', '')} is currently {status}."
        )

    if return_action_completed or wants_refund:
        return {
            "resolution_success": False,
            "case_completed": False,
            "next_domain": "REFUND",
            "transaction_amount": amount,
            "transaction_currency": currency,
            "resolution_result": {
                "operation": "RETURN_VALIDATED",
                "order_id": order_id,
                "return_id": ret.get("return_id", ""),
                "return_status": status,
            },
            "resolution_failure_reason": "",
            "status": "DOMAIN_COMPLETED",
        }

    return _success({
        "operation": "RETURN_INFORMATION_VALIDATED",
        "order_id": order_id,
        "return_id": ret.get("return_id", ""),
        "return_status": status,
    })

def validate_resolution(state: dict[str, Any]) -> dict[str, Any]:
    action_result = state.get("action_result", {}) or {}
    if action_result and action_result.get("success") is False and not action_result.get("replan"):
        return _failure(action_result.get("message", action_result.get("error_code", "The action failed.")))

    domain = str(state.get("domain") or state.get("issue_type") or "").upper().strip()
    if domain in {"ORDER", "PAYMENT", "PRODUCT_QUERY"}:
        return _validate_information_domain(state, domain)
    if domain == "DELIVERY":
        return _validate_delivery(state)
    if domain == "REFUND":
        return _validate_refund(state)
    if domain == "CANCELLATION":
        return _validate_cancellation(state)
    if domain == "RETURN":
        return _validate_return(state)
    return _failure(f"No validation logic is defined for domain '{domain}'.")
