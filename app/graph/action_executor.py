from __future__ import annotations

from typing import Any

from app.tools.action_tools import create_refund

HUMAN_APPROVAL_THRESHOLD = 2000.0


def execute_action(state) -> dict[str, Any]:
    """
    Execute an action only after the CasePilot authorization
    rules have been satisfied.

    High-value actions (>= ₹2,000) require explicit human
    approval before execution.
    """

    action_type = str(
        state.get("action_type", "")
    ).upper()

    amount = state.get("transaction_amount")

    # -------------------------------------------------
    # Authorization safety check
    # -------------------------------------------------

    if amount is not None:
        amount = float(amount)

        if amount >= HUMAN_APPROVAL_THRESHOLD:
            approval = str(
                state.get("human_approval", "")
            ).upper()

            if approval != "APPROVED":
                return {
                    "action_authorized": False,
                    "action_result": {
                        "success": False,
                        "error_code": "HUMAN_APPROVAL_REQUIRED",
                        "message": (
                            f"Transaction amount ₹{amount:.2f} "
                            "requires human approval before "
                            "the action can be executed."
                        ),
                    },
                    "status": "WAITING_FOR_HUMAN_APPROVAL",
                }

    # -------------------------------------------------
    # CREATE REFUND
    # -------------------------------------------------

    if action_type == "CREATE_REFUND":

        order_id = state.get("order_id")

        if not order_id:
            return {
                "action_authorized": True,
                "action_result": {
                    "success": False,
                    "error_code": "ORDER_ID_MISSING",
                    "message": (
                        "Order ID is required for a refund."
                    ),
                },
                "status": "ACTION_FAILED",
            }

        if amount is None:
            return {
                "action_authorized": True,
                "action_result": {
                    "success": False,
                    "error_code": "AMOUNT_MISSING",
                    "message": (
                        "Refund amount could not be determined."
                    ),
                },
                "status": "ACTION_FAILED",
            }

        result = create_refund.invoke(
            {
                "order_id": order_id,
                "amount": float(amount),
                "reason": state.get(
                    "issue_type",
                    "Customer refund request",
                ),
            }
        )

        return {
            "action_authorized": True,
            "action_result": result,
            "status": (
                "ACTION_COMPLETED"
                if result.get("success")
                else "ACTION_FAILED"
            ),
        }

    # -------------------------------------------------
    # OTHER ACTIONS
    # -------------------------------------------------

    return {
        "action_authorized": True,
        "action_result": {
            "success": False,
            "error_code": "ACTION_NOT_IMPLEMENTED",
            "message": (
                f"Action '{action_type}' is not implemented yet."
            ),
        },
        "status": "ACTION_FAILED",
    }