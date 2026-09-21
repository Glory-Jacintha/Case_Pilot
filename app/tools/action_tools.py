from __future__ import annotations

from langchain.tools import tool

from app.db.postgres import DatabaseError, get_connection, fetch_one


def _next_refund_id(connection) -> str:
    """
    Generate the next synthetic refund ID from the highest
    numeric REF######## ID currently stored in PostgreSQL.

    An advisory transaction lock prevents two concurrent refund
    operations from generating the same ID.
    """

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT pg_advisory_xact_lock(
                hashtext('casepilot_refund_id_generation')
            )
            """
        )

        cursor.execute(
            """
            SELECT COALESCE(
                MAX(
                    CASE
                        WHEN refund_id ~ '^REF[0-9]+$'
                        THEN CAST(
                            SUBSTRING(refund_id FROM 4)
                            AS BIGINT
                        )
                        ELSE 0
                    END
                ),
                0
            )
            FROM refunds
            """
        )

        highest_number = cursor.fetchone()[0]

    return f"REF{int(highest_number) + 1:08d}"


@tool
def create_refund(
    order_id: str,
    amount: float,
    reason: str,
) -> dict:
    """
    Create or initiate a synthetic refund for a CasePilot order.

    This modifies the CasePilot operational data stored in
    PostgreSQL RDS. It does not interact with Amazon, banks,
    payment gateways, or any real financial system.

    If an existing refund record has NOT_INITIATED status,
    that record is updated instead of creating a duplicate.

    Args:
        order_id: The order ID.
        amount: The amount to refund.
        reason: The reason for the refund.
    """

    order_id = str(order_id).strip()
    reason = str(reason).strip()

    # =========================================================
    # 1. Find and validate the order
    # =========================================================

    try:
        with get_connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        order_id,
                        customer_id,
                        total_amount
                    FROM orders
                    WHERE order_id = %s
                    FOR SHARE
                    """,
                    (order_id,),
                )

                order = cursor.fetchone()

                if not order:
                    return {
                        "success": False,
                        "error_code": "ORDER_NOT_FOUND",
                        "message": (
                            f"Order {order_id} was not found."
                        ),
                    }

                order_columns = [
                    column.name
                    for column in cursor.description
                ]

                order = dict(
                    zip(order_columns, order)
                )

                # =================================================
                # 2. Validate order amount
                # =================================================

                try:
                    order_amount = float(
                        order["total_amount"]
                    )
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
                        "message": (
                            "Refund amount must be greater "
                            "than zero."
                        ),
                    }

                if amount > order_amount:
                    return {
                        "success": False,
                        "error_code": (
                            "REFUND_EXCEEDS_ORDER_AMOUNT"
                        ),
                        "message": (
                            f"Requested refund "
                            f"₹{amount:.2f} exceeds "
                            f"the order amount "
                            f"₹{order_amount:.2f}."
                        ),
                    }

                # =================================================
                # 3. Find successful payment
                # =================================================

                cursor.execute(
                    """
                    SELECT
                        transaction_id,
                        payment_status,
                        gateway_reference
                    FROM payments
                    WHERE order_id = %s
                    ORDER BY transaction_date DESC
                    LIMIT 1
                    """,
                    (order_id,),
                )

                payment_row = cursor.fetchone()

                if not payment_row:
                    return {
                        "success": False,
                        "error_code": "PAYMENT_NOT_FOUND",
                        "message": (
                            f"No payment record was found "
                            f"for {order_id}."
                        ),
                    }

                payment_columns = [
                    column.name
                    for column in cursor.description
                ]

                payment = dict(
                    zip(payment_columns, payment_row)
                )

                payment_status = str(
                    payment.get("payment_status", "")
                ).upper()

                if payment_status != "SUCCESS":
                    return {
                        "success": False,
                        "error_code": (
                            "PAYMENT_NOT_SUCCESSFUL"
                        ),
                        "message": (
                            f"Payment status is "
                            f"{payment_status or 'UNKNOWN'}; "
                            "refund cannot be created."
                        ),
                    }

                # =================================================
                # 4. Lock refund ID generation
                # =================================================

                cursor.execute(
                    """
                    SELECT pg_advisory_xact_lock(
                        hashtext(
                            'casepilot_refund_operation'
                        )
                    )
                    """
                )

                # =================================================
                # 5. Check existing refund
                # =================================================

                cursor.execute(
                    """
                    SELECT
                        refund_id,
                        refund_amount,
                        refund_status
                    FROM refunds
                    WHERE order_id = %s
                    ORDER BY requested_date DESC NULLS LAST
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (order_id,),
                )

                refund_row = cursor.fetchone()

                if refund_row:
                    refund_columns = [
                        column.name
                        for column in cursor.description
                    ]

                    existing_refund = dict(
                        zip(refund_columns, refund_row)
                    )

                    existing_status = str(
                        existing_refund.get(
                            "refund_status",
                            "",
                        )
                    ).upper()

                    existing_amount = float(
                        existing_refund.get(
                            "refund_amount",
                            0,
                        ) or 0
                    )

                    # ---------------------------------------------
                    # Already completed
                    # ---------------------------------------------

                    if existing_status == "COMPLETED":
                        return {
                            "success": False,
                            "error_code": (
                                "REFUND_ALREADY_COMPLETED"
                            ),
                            "message": (
                                f"Refund "
                                f"{existing_refund.get('refund_id')} "
                                "has already been completed."
                            ),
                        }

                    # ---------------------------------------------
                    # Already processing
                    # ---------------------------------------------

                    if existing_status == "PROCESSING":
                        return {
                            "success": False,
                            "error_code": (
                                "REFUND_ALREADY_PROCESSING"
                            ),
                            "message": (
                                f"Refund "
                                f"{existing_refund.get('refund_id')} "
                                "is already being processed."
                            ),
                        }

                    # ---------------------------------------------
                    # Existing NOT_INITIATED refund
                    # ---------------------------------------------

                    if existing_status == "NOT_INITIATED":

                        if abs(
                            existing_amount - amount
                        ) > 0.01:
                            return {
                                "success": False,
                                "error_code": (
                                    "REFUND_AMOUNT_MISMATCH"
                                ),
                                "message": (
                                    f"Existing refund amount is "
                                    f"₹{existing_amount:.2f}, "
                                    f"but ₹{amount:.2f} "
                                    "was requested."
                                ),
                            }

                        cursor.execute(
                            """
                            UPDATE refunds
                            SET
                                refund_status = 'PROCESSING',
                                refund_reason = %s,
                                requested_date = CURRENT_TIMESTAMP
                            WHERE refund_id = %s
                            RETURNING
                                refund_id,
                                refund_status,
                                refund_amount
                            """,
                            (
                                reason,
                                existing_refund["refund_id"],
                            ),
                        )

                        updated = cursor.fetchone()

                        if not updated:
                            return {
                                "success": False,
                                "error_code": (
                                    "REFUND_UPDATE_FAILED"
                                ),
                                "message": (
                                    "The existing refund "
                                    "could not be updated."
                                ),
                            }

                        return {
                            "success": True,
                            "operation": "UPDATE_REFUND",
                            "refund_id": updated[0],
                            "order_id": order_id,
                            "amount": float(updated[2]),
                            "status": updated[1],
                            "reason": reason,
                            "message": (
                                f"Existing refund "
                                f"{updated[0]} was moved "
                                "from NOT_INITIATED "
                                "to PROCESSING."
                            ),
                        }

                # =================================================
                # 6. No existing refund → create new one
                # =================================================

                refund_id = _next_refund_id(
                    connection
                )

                cursor.execute(
                    """
                    INSERT INTO refunds (
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
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        'PROCESSING',
                        %s,
                        CURRENT_TIMESTAMP,
                        NULL,
                        %s
                    )
                    RETURNING
                        refund_id,
                        order_id,
                        refund_amount,
                        refund_status,
                        refund_reason,
                        requested_date
                    """,
                    (
                        refund_id,
                        order_id,
                        order["customer_id"],
                        payment["transaction_id"],
                        amount,
                        reason,
                        payment.get(
                            "gateway_reference"
                        ),
                    ),
                )

                created = cursor.fetchone()

                if not created:
                    return {
                        "success": False,
                        "error_code": (
                            "REFUND_CREATE_FAILED"
                        ),
                        "message": (
                            "The refund could not be created."
                        ),
                    }

                return {
                    "success": True,
                    "operation": "CREATE_REFUND",
                    "refund_id": created[0],
                    "order_id": created[1],
                    "amount": float(created[2]),
                    "status": created[3],
                    "reason": created[4],
                    "message": (
                        f"Refund {created[0]} was created "
                        f"successfully for "
                        f"₹{float(created[2]):.2f}."
                    ),
                }

    except DatabaseError as exc:
        return {
            "success": False,
            "error_code": "DATABASE_ERROR",
            "message": str(exc),
        }