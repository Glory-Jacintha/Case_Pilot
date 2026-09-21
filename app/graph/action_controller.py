from __future__ import annotations

from typing import Any


def determine_action(state) -> dict[str, Any]:
    """
    Determine whether the case requires a write/transaction action.

    This node only decides what action is required.
    It does NOT execute the action.
    """

    domain = str(
        state.get("domain", "")
    ).upper()

    # -------------------------------------------------
    # REFUND
    # -------------------------------------------------

    if domain == "REFUND":
        return {
            "action_required": True,
            "action_type": "CREATE_REFUND",
            "action_reason": (
                "The customer refund request requires "
                "a refund transaction."
            ),
            "status": "ACTION_REQUIRED",
        }

    # -------------------------------------------------
    # CANCELLATION
    # -------------------------------------------------

    if domain == "CANCELLATION":
        return {
            "action_required": True,
            "action_type": "CANCEL_ORDER",
            "action_reason": (
                "The customer requested order cancellation."
            ),
            "status": "ACTION_REQUIRED",
        }

    # -------------------------------------------------
    # INFORMATION-ONLY DOMAINS
    # -------------------------------------------------

    return {
        "action_required": False,
        "action_type": "",
        "action_reason": "",
        "action_result": state.get(
            "resolution_result",
            {},
        ),
        "status": "NO_ACTION_REQUIRED",
    }