from __future__ import annotations

from langchain.tools import tool

from app.db.postgres import DatabaseError, fetch_all, fetch_one


@tool
def get_order_details(order_id: str) -> dict:
    """Retrieve the order record for a given order ID."""
    try:
        order = fetch_one(
            """
            SELECT
                order_id,
                order_date,
                customer_id,
                customer_name,
                product_id,
                product_name,
                category,
                brand,
                quantity,
                unit_price,
                discount,
                tax,
                shipping_cost,
                total_amount,
                payment_method,
                order_status,
                city,
                state,
                country,
                seller_id
            FROM orders
            WHERE order_id = %s
            """,
            (str(order_id).strip(),),
        )

        if not order:
            return {
                "success": False,
                "error": f"Order {order_id} was not found.",
            }

        return {
            "success": True,
            "order": order,
        }

    except DatabaseError as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def get_customer_details(customer_id: str) -> dict:
    """Retrieve basic customer information for a given customer ID."""
    try:
        customer = fetch_one(
            """
            SELECT
                customer_id,
                customer_name,
                city,
                state,
                country
            FROM customers
            WHERE customer_id = %s
            """,
            (str(customer_id).strip(),),
        )

        if not customer:
            return {
                "success": False,
                "error": f"Customer {customer_id} was not found.",
            }

        return {
            "success": True,
            "customer": customer,
        }

    except DatabaseError as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def get_payment_details(order_id: str) -> dict:
    """Retrieve the payment transaction associated with an order."""
    try:
        payment = fetch_one(
            """
            SELECT
                transaction_id,
                order_id,
                customer_id,
                amount,
                payment_method,
                payment_status,
                transaction_date,
                gateway_reference
            FROM payments
            WHERE order_id = %s
            ORDER BY transaction_date DESC
            LIMIT 1
            """,
            (str(order_id).strip(),),
        )

        if not payment:
            return {
                "success": False,
                "error": (
                    f"No payment record was found for order {order_id}."
                ),
            }

        return {
            "success": True,
            "payment": payment,
        }

    except DatabaseError as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def get_delivery_details(order_id: str) -> dict:
    """Retrieve delivery and tracking information for an order."""
    try:
        delivery = fetch_one(
            """
            SELECT
                delivery_id,
                order_id,
                tracking_id,
                delivery_status,
                expected_date,
                actual_delivery_date,
                courier,
                delivery_attempts,
                delivery_proof
            FROM deliveries
            WHERE order_id = %s
            ORDER BY delivery_id
            LIMIT 1
            """,
            (str(order_id).strip(),),
        )

        if not delivery:
            return {
                "success": False,
                "error": (
                    f"No delivery record was found for order {order_id}."
                ),
            }

        return {
            "success": True,
            "delivery": delivery,
        }

    except DatabaseError as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def get_return_details(order_id: str) -> dict:
    """Retrieve the return record for an order, if one exists."""
    try:
        results = fetch_all(
            """
            SELECT
                return_id,
                order_id,
                customer_id,
                return_status,
                return_reason,
                requested_date,
                approved_date
            FROM returns
            WHERE order_id = %s
            ORDER BY requested_date DESC NULLS LAST
            """,
            (str(order_id).strip(),),
        )

        if not results:
            return {
                "success": True,
                "return_exists": False,
                "message": (
                    f"No return record exists for order {order_id}."
                ),
            }

        return {
            "success": True,
            "return_exists": True,
            "return": results[0],
        }

    except DatabaseError as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def get_refund_details(order_id: str) -> dict:
    """Retrieve the refund record for an order, if one exists."""
    try:
        results = fetch_all(
            """
            SELECT
                refund_id,
                order_id,
                customer_id,
                transaction_id,
                refund_amount,
                refund_status,
                refund_reason,
                requested_date,
                processed_date,
                gateway_reference
            FROM refunds
            WHERE order_id = %s
            ORDER BY requested_date DESC NULLS LAST
            """,
            (str(order_id).strip(),),
        )

        if not results:
            return {
                "success": True,
                "refund_exists": False,
                "message": (
                    f"No refund record exists for order {order_id}."
                ),
            }

        return {
            "success": True,
            "refund_exists": True,
            "refund": results[0],
        }

    except DatabaseError as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def get_product_details(product_id: str) -> dict:
    """Retrieve product return-window and returnability metadata."""
    try:
        product = fetch_one(
            """
            SELECT
                product_id,
                product_name,
                category,
                brand,
                return_window_days,
                return_eligible,
                returnless_refund_eligible,
                non_returnable_reason
            FROM products
            WHERE product_id = %s
            """,
            (str(product_id).strip(),),
        )

        if not product:
            return {
                "success": False,
                "error": (
                    f"Product {product_id} was not found."
                ),
            }

        return {
            "success": True,
            "product": product,
        }

    except DatabaseError as exc:
        return {
            "success": False,
            "error": str(exc),
        }