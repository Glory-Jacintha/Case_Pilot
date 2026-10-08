from __future__ import annotations

from langchain.tools import tool

from app.db.postgres import DatabaseError, get_connection


def _next_refund_id(connection) -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext('casepilot_refund_id_generation'))")
        cursor.execute(
            """
            SELECT COALESCE(
                MAX(CASE WHEN refund_id ~ '^REF[0-9]+$'
                         THEN CAST(SUBSTRING(refund_id FROM 4) AS BIGINT)
                         ELSE 0 END), 0)
            FROM refunds
            """
        )
        highest = cursor.fetchone()[0]
    return f"REF{int(highest) + 1:08d}"


def _next_return_id(connection) -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext('casepilot_return_id_generation'))")
        cursor.execute(
            """
            SELECT COALESCE(
                MAX(CASE WHEN return_id ~ '^RET[0-9]+$'
                         THEN CAST(SUBSTRING(return_id FROM 4) AS BIGINT)
                         ELSE 0 END), 0)
            FROM returns
            """
        )
        highest = cursor.fetchone()[0]
    return f"RET{int(highest) + 1:08d}"


@tool
def create_refund(order_id: str, amount: float, reason: str) -> dict:
    """Create or initiate a refund in CasePilot PostgreSQL RDS."""
    order_id = str(order_id or "").strip()
    reason = str(reason or "").strip()

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT order_id, customer_id, total_amount
                    FROM orders WHERE order_id = %s FOR SHARE
                    """,
                    (order_id,),
                )
                order_row = cursor.fetchone()
                if not order_row:
                    return {"success": False, "error_code": "ORDER_NOT_FOUND", "message": f"Order {order_id} was not found."}
                order = dict(zip([d.name for d in cursor.description], order_row))
                order_amount = float(order["total_amount"])

                if amount <= 0:
                    return {"success": False, "error_code": "INVALID_REFUND_AMOUNT", "message": "Refund amount must be greater than zero."}
                if abs(float(amount) - order_amount) > 0.01:
                    return {
                        "success": False,
                        "error_code": "REFUND_AMOUNT_MISMATCH",
                        "message": "The requested refund amount does not match the verified order amount.",
                    }

                cursor.execute(
                    """
                    SELECT transaction_id, payment_status, gateway_reference
                    FROM payments WHERE order_id = %s
                    ORDER BY transaction_date DESC LIMIT 1
                    """,
                    (order_id,),
                )
                payment_row = cursor.fetchone()
                if not payment_row:
                    return {"success": False, "error_code": "PAYMENT_NOT_FOUND", "message": f"No payment record was found for {order_id}."}
                payment = dict(zip([d.name for d in cursor.description], payment_row))
                if str(payment.get("payment_status", "")).upper() != "SUCCESS":
                    return {"success": False, "error_code": "PAYMENT_NOT_SUCCESSFUL", "message": f"Payment status is {payment.get('payment_status') or 'UNKNOWN'}; refund cannot be created."}

                cursor.execute(
                    """
                    SELECT refund_id, refund_amount, refund_status
                    FROM refunds WHERE order_id = %s
                    ORDER BY requested_date DESC NULLS LAST LIMIT 1 FOR UPDATE
                    """,
                    (order_id,),
                )
                existing_row = cursor.fetchone()
                if existing_row:
                    existing = dict(zip([d.name for d in cursor.description], existing_row))
                    status = str(existing["refund_status"] or "").upper()
                    existing_amount = float(existing["refund_amount"] or 0)
                    if status == "COMPLETED":
                        return {"success": False, "error_code": "REFUND_ALREADY_COMPLETED", "message": f"Refund {existing['refund_id']} has already been completed."}
                    if status == "PROCESSING":
                        return {"success": False, "error_code": "REFUND_ALREADY_PROCESSING", "message": f"Refund {existing['refund_id']} is already being processed."}
                    if status == "NOT_INITIATED":
                        if abs(existing_amount - order_amount) > 0.01:
                            return {"success": False, "error_code": "REFUND_AMOUNT_MISMATCH", "message": "The existing refund amount does not match the verified order amount."}
                        cursor.execute(
                            """
                            UPDATE refunds SET refund_status='PROCESSING', refund_reason=%s,
                            requested_date=CURRENT_TIMESTAMP
                            WHERE refund_id=%s
                            RETURNING refund_id, order_id, refund_amount, refund_status, refund_reason
                            """,
                            (reason, existing["refund_id"]),
                        )
                        row = cursor.fetchone()
                        return {
                            "success": True, "operation": "UPDATE_REFUND",
                            "refund_id": row[0], "order_id": row[1], "amount": float(row[2]),
                            "status": row[3], "reason": row[4],
                            "message": f"Refund {row[0]} was moved to PROCESSING.",
                        }

                refund_id = _next_refund_id(connection)
                cursor.execute(
                    """
                    INSERT INTO refunds (
                        refund_id, order_id, customer_id, transaction_id,
                        refund_amount, refund_status, refund_reason,
                        requested_date, processed_date, gateway_reference
                    ) VALUES (%s,%s,%s,%s,%s,'PROCESSING',%s,CURRENT_TIMESTAMP,NULL,%s)
                    RETURNING refund_id, order_id, refund_amount, refund_status, refund_reason
                    """,
                    (refund_id, order_id, order["customer_id"], payment["transaction_id"], order_amount, reason, payment.get("gateway_reference")),
                )
                row = cursor.fetchone()
                return {
                    "success": True, "operation": "CREATE_REFUND", "refund_id": row[0],
                    "order_id": row[1], "amount": float(row[2]), "status": row[3],
                    "reason": row[4], "message": f"Refund {row[0]} was created successfully.",
                }
    except DatabaseError as exc:
        return {"success": False, "error_code": "DATABASE_ERROR", "message": str(exc)}


@tool
def cancel_order(order_id: str, reason: str = "Customer cancellation request") -> dict:
    """Cancel an eligible order, or return a safe replan when cancellation is impossible."""
    order_id = str(order_id or "").strip()
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT order_id, customer_id, total_amount, order_status
                    FROM orders WHERE order_id=%s FOR UPDATE
                    """,
                    (order_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return {"success": False, "error_code": "ORDER_NOT_FOUND", "message": f"Order {order_id} was not found."}
                order = dict(zip([d.name for d in cursor.description], row))
                status = str(order["order_status"] or "").upper()

                if status == "CANCELLED":
                    return {
                        "success": True, "operation": "CANCEL_ORDER", "already_completed": True,
                        "order_id": order_id, "customer_id": order["customer_id"],
                        "amount": float(order["total_amount"]), "order_status": "CANCELLED",
                        "next_domain": "REFUND", "message": f"Order {order_id} is already cancelled.",
                    }

                non_cancellable = {"DELIVERED", "RETURNED", "SHIPPED", "OUT_FOR_DELIVERY"}
                if status in non_cancellable:
                    return {
                        "success": False, "replan": True, "next_domain": "RETURN",
                        "error_code": "CANCELLATION_NOT_POSSIBLE",
                        "message": f"Order {order_id} is {status.lower()} and cannot be cancelled. A return is the next supported path.",
                        "order_id": order_id, "amount": float(order["total_amount"]),
                    }

                cursor.execute(
                    "UPDATE orders SET order_status='CANCELLED' WHERE order_id=%s RETURNING order_id, order_status, total_amount, customer_id",
                    (order_id,),
                )
                updated = cursor.fetchone()
                return {
                    "success": True, "operation": "CANCEL_ORDER", "order_id": updated[0],
                    "order_status": updated[1], "amount": float(updated[2]), "customer_id": updated[3],
                    "next_domain": "REFUND", "message": f"Order {order_id} was cancelled successfully.",
                    "reason": reason,
                }
    except DatabaseError as exc:
        return {"success": False, "error_code": "DATABASE_ERROR", "message": str(exc)}


@tool
def process_return(order_id: str, reason: str = "Customer return request") -> dict:
    """Create/complete a return record for an order in PostgreSQL RDS."""
    order_id = str(order_id or "").strip()
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT order_id, customer_id, total_amount, order_status, product_id
                    FROM orders WHERE order_id=%s FOR UPDATE
                    """,
                    (order_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return {"success": False, "error_code": "ORDER_NOT_FOUND", "message": f"Order {order_id} was not found."}
                order = dict(zip([d.name for d in cursor.description], row))
                status = str(order["order_status"] or "").upper()

                cursor.execute(
                    """
                    SELECT return_id, return_status FROM returns
                    WHERE order_id=%s ORDER BY requested_date DESC NULLS LAST LIMIT 1 FOR UPDATE
                    """,
                    (order_id,),
                )
                existing_row = cursor.fetchone()
                if existing_row:
                    existing = dict(zip([d.name for d in cursor.description], existing_row))
                    existing_status = str(existing["return_status"] or "").upper()
                    if existing_status in {"RECEIVED", "COMPLETED"}:
                        return {
                            "success": True, "operation": "PROCESS_RETURN", "already_completed": True,
                            "return_id": existing["return_id"], "order_id": order_id,
                            "return_status": existing_status, "amount": float(order["total_amount"]),
                            "next_domain": "REFUND", "message": f"Return {existing['return_id']} is already completed.",
                        }
                    cursor.execute(
                        "UPDATE returns SET return_status='COMPLETED', return_reason=%s WHERE return_id=%s RETURNING return_id, return_status",
                        (reason, existing["return_id"]),
                    )
                    ret = cursor.fetchone()
                    cursor.execute("UPDATE orders SET order_status='RETURNED' WHERE order_id=%s", (order_id,))
                    return {
                        "success": True, "operation": "PROCESS_RETURN", "return_id": ret[0], "order_id": order_id,
                        "return_status": ret[1], "amount": float(order["total_amount"]), "next_domain": "REFUND",
                        "message": f"Return {ret[0]} was completed.",
                    }

                if status == "CANCELLED":
                    return {"success": False, "error_code": "RETURN_NOT_REQUIRED", "message": f"Order {order_id} is cancelled; a return is not required."}

                return_id = _next_return_id(connection)
                cursor.execute(
                    """
                    INSERT INTO returns (
                        return_id, order_id, customer_id, return_status,
                        return_reason, requested_date, approved_date
                    ) VALUES (%s,%s,%s,'COMPLETED',%s,CURRENT_DATE,CURRENT_DATE)
                    RETURNING return_id, return_status
                    """,
                    (return_id, order_id, order["customer_id"], reason),
                )
                ret = cursor.fetchone()
                cursor.execute("UPDATE orders SET order_status='RETURNED' WHERE order_id=%s", (order_id,))
                return {
                    "success": True, "operation": "PROCESS_RETURN", "return_id": ret[0], "order_id": order_id,
                    "return_status": ret[1], "amount": float(order["total_amount"]), "next_domain": "REFUND",
                    "message": f"Return {ret[0]} was processed successfully.",
                }
    except DatabaseError as exc:
        return {"success": False, "error_code": "DATABASE_ERROR", "message": str(exc)}
