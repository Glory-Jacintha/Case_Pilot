from typing import Literal


Domain = Literal[
    "ORDER",
    "PAYMENT",
    "DELIVERY",
    "REFUND",
    "RETURN",
    "CANCELLATION",
    "PRODUCT_QUERY",
]


SUPPORTED_DOMAINS = [
    "ORDER",
    "PAYMENT",
    "DELIVERY",
    "REFUND",
    "RETURN",
    "CANCELLATION",
    "PRODUCT_QUERY",
]


DOMAIN_DESCRIPTIONS = {
    "ORDER": (
        "Questions about order status, order details, items, quantity, "
        "order information, or order-related problems."
    ),
    "PAYMENT": (
        "Questions about payment status, failed payments, duplicate charges, "
        "payment reconciliation, or payment transactions."
    ),
    "DELIVERY": (
        "Questions about shipment, tracking, delivery status, delayed delivery, "
        "missing delivery, or delivery disputes."
    ),
    "REFUND": (
        "Questions about refunds, refund status, refund eligibility, "
        "missing refunds, or refund processing."
    ),
    "RETURN": (
        "Questions about returning an item, return eligibility, return status, "
        "return windows, or return-related problems."
    ),
    "CANCELLATION": (
        "Questions about cancelling an order, cancellation eligibility, "
        "or cancellation status."
    ),
    "PRODUCT_QUERY": (
        "Questions about product information, product availability, "
        "product characteristics, category, brand, or product policy."
    ),
}