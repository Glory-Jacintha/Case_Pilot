from __future__ import annotations

from langchain.tools import tool
from app.db.postgres import DatabaseError, fetch_one


@tool
def get_refund_details_by_id(refund_id: str) -> dict:
    """Retrieve an exact refund record by RefundID from PostgreSQL RDS."""
    refund_id = str(refund_id or "").strip()
    if not refund_id:
        return {"success": False, "error_code": "REFUND_ID_REQUIRED", "message": "Refund ID is required."}
    try:
        row = fetch_one(
            """
            SELECT refund_id, order_id, customer_id, transaction_id,
                   refund_amount, refund_status, refund_reason,
                   requested_date, processed_date, gateway_reference
            FROM refunds WHERE refund_id = %s
            """,
            (refund_id,),
        )
        if not row:
            return {"success": False, "error_code": "REFUND_NOT_FOUND", "message": f"Refund {refund_id} was not found."}
        return {"success": True, "refund_exists": True, "refund": row}
    except DatabaseError as exc:
        return {"success": False, "error_code": "DATABASE_ERROR", "message": str(exc)}
