from __future__ import annotations

from typing import TypedDict

from .domains import SUPPORTED_DOMAINS


class StrategyDefinition(TypedDict):
    name: str
    description: str


DOMAIN_STRATEGIES: dict[str, list[StrategyDefinition]] = {
    "ORDER": [
        {
            "name": "ORDER_STATUS_CHECK",
            "description": "Check the current order status and order details.",
        },
        {
            "name": "ORDER_DETAILS_REVIEW",
            "description": "Review order items, quantity, amount, and customer/order information.",
        },
        {
            "name": "ORDER_STATUS_RECHECK",
            "description": "Re-check the order state when the first investigation is inconclusive.",
        },
    ],

    "PAYMENT": [
        {
            "name": "PAYMENT_STATUS_CHECK",
            "description": "Check the payment transaction status.",
        },
        {
            "name": "PAYMENT_RECONCILIATION",
            "description": "Compare the payment transaction with the associated order.",
        },
        {
            "name": "PAYMENT_REFERENCE_REVIEW",
            "description": "Review the payment gateway reference and transaction evidence.",
        },
    ],

    "DELIVERY": [
        {
            "name": "DELIVERY_TRACKING_RECHECK",
            "description": "Re-check shipment tracking and delivery status.",
        },
        {
            "name": "DELIVERY_PROOF_REVIEW",
            "description": "Review available delivery proof and delivery attempts.",
        },
        {
            "name": "DELIVERY_EXCEPTION_REVIEW",
            "description": "Review delivery evidence for missing, delayed, or disputed delivery.",
        },
    ],

    "REFUND": [
        {
            "name": "REFUND_STATUS_CHECK",
            "description": "Check the current refund status and refund record.",
        },
        {
            "name": "REFUND_TRANSACTION_RECONCILIATION",
            "description": "Reconcile the refund with the original payment transaction.",
        },
        {
            "name": "REFUND_ELIGIBILITY_REVIEW",
            "description": "Review refund eligibility using product, order, and policy information.",
        },
    ],

    "RETURN": [
        {
            "name": "RETURN_ELIGIBILITY_CHECK",
            "description": "Check whether the product and order are eligible for return.",
        },
        {
            "name": "RETURN_STATUS_CHECK",
            "description": "Check the current return status.",
        },
        {
            "name": "RETURN_POLICY_REVIEW",
            "description": "Review the applicable return window and product policy.",
        },
    ],

    "CANCELLATION": [
        {
            "name": "CANCELLATION_ELIGIBILITY_CHECK",
            "description": "Check whether the order can currently be cancelled.",
        },
        {
            "name": "ORDER_STATE_REVIEW",
            "description": "Review the current order state to determine cancellation feasibility.",
        },
        {
            "name": "CANCELLATION_STATUS_RECHECK",
            "description": "Re-check cancellation-related order information.",
        },
    ],

    "PRODUCT_QUERY": [
        {
            "name": "PRODUCT_DETAILS_CHECK",
            "description": "Retrieve the product's available information and characteristics.",
        },
        {
            "name": "PRODUCT_POLICY_REVIEW",
            "description": "Review relevant product-related policy information.",
        },
        {
            "name": "PRODUCT_INFORMATION_RECHECK",
            "description": "Re-check product information when the first investigation is incomplete.",
        },
    ],
}


def get_strategies_for_domain(domain: str) -> list[StrategyDefinition]:
    """
    Return the resolution/investigation strategies available
    for the selected CasePilot domain.
    """

    if domain not in SUPPORTED_DOMAINS:
        raise ValueError(f"Unsupported CasePilot domain: {domain}")

    return DOMAIN_STRATEGIES[domain]