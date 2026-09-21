from __future__ import annotations

from app.db.postgres import get_connection
from app.graph.graph import casepilot_graph
from app.tools.read_tools import get_refund_details


# ============================================================
# TEST DATA DISCOVERY
# ============================================================

def find_clean_low_value_order():
    """
    Dynamically find a low-value order in RDS that:

    - is below ₹2,000
    - has a successful payment
    - currently has no refund

    This avoids hardcoding an order ID.
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    o.order_id,
                    o.total_amount
                FROM orders o
                JOIN payments p
                    ON p.order_id = o.order_id
                LEFT JOIN refunds r
                    ON r.order_id = o.order_id
                WHERE o.total_amount < 2000
                  AND p.payment_status = 'SUCCESS'
                  AND r.order_id IS NULL
                ORDER BY o.order_id
                LIMIT 1;
                """
            )

            row = cursor.fetchone()

            if not row:
                raise AssertionError(
                    "No clean low-value order was found in RDS."
                )

            order_id, order_amount = row

            return (
                str(order_id),
                float(order_amount),
            )


# ============================================================
# LOW-VALUE REFUND END-TO-END TEST
# ============================================================

def test_low_value_refund_end_to_end():

    # ---------------------------------------------------------
    # 1. Discover a suitable RDS test order
    # ---------------------------------------------------------

    order_id, order_amount = find_clean_low_value_order()

    thread_id = f"test-refund-real-{order_id}"

    customer_message = (
        f"I want a refund for order {order_id} "
        "because I no longer want the item."
    )

    print("\n")
    print("=" * 60)
    print("REAL LOW-VALUE REFUND INTEGRATION TEST")
    print("=" * 60)

    print(
        "SELECTED ORDER:",
        order_id,
    )

    print(
        "ORDER AMOUNT:",
        order_amount,
    )

    print(
        "SOURCE:",
        "RDS",
    )

    print(
        "ACTION:",
        "real create_refund tool",
    )

    created_refund_id = None

    try:

        # -----------------------------------------------------
        # 2. Run the actual CasePilot graph
        # -----------------------------------------------------

        state = {
            "session_id": thread_id,
            "customer_message": customer_message,
            "conversation_history": [
                {
                    "role": "user",
                    "content": customer_message,
                }
            ],
        }

        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        result = casepilot_graph.invoke(
            state,
            config=config,
        )

        # -----------------------------------------------------
        # 3. Debug output
        # -----------------------------------------------------

        print("\n--- GRAPH RESULT ---")

        print(
            "DOMAIN:",
            result.get("domain"),
        )

        print(
            "TRANSACTION_AMOUNT:",
            result.get("transaction_amount"),
        )

        print(
            "AUTHORIZATION:",
            result.get("authorization"),
        )

        print(
            "ATTEMPTED_STRATEGIES:",
            result.get("attempted_strategies"),
        )

        print(
            "ACTION_READY:",
            result.get("action_ready"),
        )

        print(
            "ACTION_REQUIRED:",
            result.get("action_required"),
        )

        print(
            "ACTION_TYPE:",
            result.get("action_type"),
        )

        print(
            "ACTION_RESULT:",
            result.get("action_result"),
        )

        print(
            "RESOLUTION_SUCCESS:",
            result.get("resolution_success"),
        )

        print(
            "STATUS:",
            result.get("status"),
        )

        print(
            "REQUIRES_HUMAN:",
            result.get("requires_human"),
        )

        print(
            "CUSTOMER_RESPONSE:",
            result.get("customer_response"),
        )

        # -----------------------------------------------------
        # 4. Validate graph routing
        # -----------------------------------------------------

        assert result["domain"] == "REFUND"

        assert (
            float(result["transaction_amount"])
            == order_amount
        )

        assert (
            result["authorization"]
            == "AI_ALLOWED"
        )

        # -----------------------------------------------------
        # 5. Validate action selection
        # -----------------------------------------------------

        assert (
            result["action_required"]
            is True
        )

        assert (
            result["action_type"]
            == "CREATE_REFUND"
        )

        # -----------------------------------------------------
        # 6. Validate actual action result
        # -----------------------------------------------------

        action_result = result.get(
            "action_result",
            {},
        )

        assert (
            action_result.get("success")
            is True
        )

        assert (
            action_result.get("operation")
            == "CREATE_REFUND"
        )

        assert (
            action_result.get("order_id")
            == order_id
        )

        assert (
            float(action_result.get("amount"))
            == order_amount
        )

        # -----------------------------------------------------
        # 7. Validate final resolution
        # -----------------------------------------------------

        assert (
            result["resolution_success"]
            is True
        )

        assert (
            result["status"]
            == "RESOLUTION_COMPLETED"
        )

        assert (
            result["requires_human"]
            is False
        )

        assert (
            result["customer_response"]
        )

        # -----------------------------------------------------
        # 8. Verify refund directly in RDS
        # -----------------------------------------------------

        refund_result = get_refund_details.invoke(
            {
                "order_id": order_id,
            }
        )

        assert (
            refund_result["success"]
            is True
        )

        assert (
            refund_result["refund_exists"]
            is True
        )

        refund = refund_result["refund"]

        created_refund_id = refund["refund_id"]

        assert (
            refund["order_id"]
            == order_id
        )

        assert (
            float(refund["refund_amount"])
            == order_amount
        )

        assert (
            refund["refund_status"]
            == "PROCESSING"
        )

        print(
            "\nREAL RDS REFUND RECORD:",
            refund,
        )

        print(
            "\nREAL RDS REFUND ACTION VERIFIED."
        )

    finally:

        # -----------------------------------------------------
        # 9. Always clean up the temporary RDS refund
        # -----------------------------------------------------

        if created_refund_id:

            with get_connection() as connection:

                with connection.cursor() as cursor:

                    cursor.execute(
                        """
                        DELETE FROM refunds
                        WHERE refund_id = %s
                        RETURNING refund_id;
                        """,
                        (
                            created_refund_id,
                        ),
                    )

                    deleted = cursor.fetchone()

                    if deleted:

                        print(
                            "\nTest RDS refund cleaned up:",
                            deleted[0],
                        )

        print(
            "\nRDS test cleanup completed."
        )