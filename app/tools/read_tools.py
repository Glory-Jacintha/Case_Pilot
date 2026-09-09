from __future__ import annotations

from langchain.tools import tool

from .data_store import (
    DataStoreError,
    customers,
    deliveries,
    find_one,
    orders,
    payments,
    products,
    refunds,
    returns,
)


@tool
def get_order_details(order_id: str) -> dict:
    """Retrieve the order record for a given order ID."""
    try:
        order = find_one(orders(), "OrderID", order_id)
        if not order:
            return {"success": False, "error": f"Order {order_id} was not found."}

        return {"success": True, "order": order}
    except DataStoreError as exc:
        return {"success": False, "error": str(exc)}


@tool
def get_customer_details(customer_id: str) -> dict:
    """Retrieve basic customer information for a given customer ID."""
    try:
        customer = find_one(customers(), "CustomerID", customer_id)
        if not customer:
            return {
                "success": False,
                "error": f"Customer {customer_id} was not found.",
            }

        return {"success": True, "customer": customer}
    except DataStoreError as exc:
        return {"success": False, "error": str(exc)}


@tool
def get_payment_details(order_id: str) -> dict:
    """Retrieve the payment transaction associated with an order."""
    try:
        payment = find_one(payments(), "OrderID", order_id)
        if not payment:
            return {
                "success": False,
                "error": f"No payment record was found for order {order_id}.",
            }

        return {"success": True, "payment": payment}
    except DataStoreError as exc:
        return {"success": False, "error": str(exc)}


@tool
def get_delivery_details(order_id: str) -> dict:
    """Retrieve tracking, delivery status, delivery proof, and courier information for an order."""
    try:
        delivery = find_one(deliveries(), "OrderID", order_id)
        if not delivery:
            return {
                "success": False,
                "error": f"No delivery record was found for order {order_id}.",
            }

        return {"success": True, "delivery": delivery}
    except DataStoreError as exc:
        return {"success": False, "error": str(exc)}


@tool
def get_return_details(order_id: str) -> dict:
    """Retrieve the return record for an order, if one exists."""
    try:
        result = [row for row in returns() if row.get("OrderID") == str(order_id).strip()]

        if not result:
            return {
                "success": True,
                "return_exists": False,
                "message": f"No return record exists for order {order_id}.",
            }

        return {
            "success": True,
            "return_exists": True,
            "return": result[0],
        }
    except DataStoreError as exc:
        return {"success": False, "error": str(exc)}


@tool
def get_refund_details(order_id: str) -> dict:
    """Retrieve the refund record for an order, if one exists."""
    try:
        result = [row for row in refunds() if row.get("OrderID") == str(order_id).strip()]

        if not result:
            return {
                "success": True,
                "refund_exists": False,
                "message": f"No refund record exists for order {order_id}.",
            }

        return {
            "success": True,
            "refund_exists": True,
            "refund": result[0],
        }
    except DataStoreError as exc:
        return {"success": False, "error": str(exc)}


@tool
def get_product_details(product_id: str) -> dict:
    """Retrieve product return-window and returnability metadata for a product ID."""
    try:
        product = find_one(products(), "ProductID", product_id)
        if not product:
            return {
                "success": False,
                "error": f"Product {product_id} was not found.",
            }

        return {"success": True, "product": product}
    except DataStoreError as exc:
        return {"success": False, "error": str(exc)}
