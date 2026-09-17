from __future__ import annotations

from app.graph.state import CaseState


def customer_response_node(state: CaseState) -> dict:
    """
    Convert internal CasePilot state into a customer-safe response.

    This node must never expose:
    - internal error codes
    - authorization flags
    - internal strategy names
    - raw investigation text
    - internal transaction metadata
    """

    status = state.get("status", "")
    resolution_success = state.get(
        "resolution_success",
        False,
    )

    resolution_result = state.get(
        "resolution_result",
        {},
    )

    failure_reason = state.get(
        "resolution_failure_reason",
        "",
    )

    order_id = state.get(
        "order_id",
        "",
    )

    # =========================================================
    # 1. Human approval required
    # =========================================================

    if status == "WAITING_FOR_HUMAN_APPROVAL":

        if order_id:
            message = (
                f"I've checked your request for order "
                f"{order_id}. Because this request requires "
                f"additional approval, I've sent it to a "
                f"support specialist for review."
            )
        else:
            message = (
                "I've checked your request and it requires "
                "additional approval. I've sent it to a "
                "support specialist for review."
            )

        return {
            "customer_response": message,
            "status": "CUSTOMER_AWAITING_HUMAN",
        }

    # =========================================================
    # 2. Successful resolution
    # =========================================================

    if resolution_success:

        operation = resolution_result.get(
            "operation",
            "",
        )

        refund_status = resolution_result.get(
            "status",
            resolution_result.get(
                "refund_status",
                "",
            ),
        )

        if operation in {
            "CREATE_REFUND",
            "UPDATE_REFUND",
        }:

            if refund_status == "PROCESSING":

                message = (
                    "I've resolved your refund request. "
                    "Your refund has been initiated and is "
                    "currently being processed. It will be "
                    "returned through the original payment method."
                )

            else:

                message = (
                    "I've successfully processed your "
                    "refund request."
                )

        else:

            message = (
                "I've successfully resolved your request."
            )

        return {
            "customer_response": message,
            "status": "RESOLUTION_COMPLETED",
        }

    # =========================================================
    # 3. All resolution strategies failed
    # =========================================================

    if status == "HUMAN_ESCALATION":

        message = (
            "I wasn't able to complete the resolution "
            "automatically after checking the available "
            "resolution options. I've sent your case to "
            "a support specialist with the investigation "
            "details so they can continue from here."
        )

        return {
            "customer_response": message,
            "status": "CUSTOMER_ESCALATED",
        }

    # =========================================================
    # 4. Missing information
    # =========================================================

    if status == "AWAITING_TRANSACTION_INFORMATION":

        message = (
            "I can help with that. Please provide your "
            "order ID so I can check the details and "
            "find the right resolution."
        )

        return {
            "customer_response": message,
            "status": "CUSTOMER_NEEDS_INFORMATION",
        }

    # =========================================================
    # 5. Investigation failure
    # =========================================================

    if status == "INVESTIGATION_FAILED":

        message = (
            "I wasn't able to retrieve enough information "
            "to resolve this request. Please provide your "
            "order ID and I'll try again."
        )

        return {
            "customer_response": message,
            "status": "CUSTOMER_NEEDS_INFORMATION",
        }

    # =========================================================
    # 6. Fallback
    # =========================================================

    message = (
        "I've checked your request. I need a little more "
        "information before I can continue. Please provide "
        "your order ID."
    )

    return {
        "customer_response": message,
        "status": "CUSTOMER_NEEDS_INFORMATION",
    }