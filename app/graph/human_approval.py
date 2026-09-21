from __future__ import annotations

from typing import Any

from langgraph.types import interrupt


def request_human_approval(
    state,
) -> dict[str, Any]:
    """
    Pause the LangGraph execution and request human approval
    for a high-value transaction.
    """

    approval_request = {
        "type": "TRANSACTION_APPROVAL",
        "action_type": state.get(
            "action_type",
            "",
        ),
        "domain": state.get(
            "domain",
            "",
        ),
        "order_id": state.get(
            "order_id",
            "",
        ),
        "transaction_amount": state.get(
            "transaction_amount",
        ),
        "reason": state.get(
            "action_reason",
            "",
        ),
        "investigation": state.get(
            "investigation",
            "",
        ),
        "resolution_result": state.get(
            "resolution_result",
            {},
        ),
    }

    human_decision = interrupt(
        approval_request
    )

    if not human_decision:
        return {
            "action_authorized": False,
            "human_approval": "REJECTED",
            "status": "HUMAN_REJECTED",
        }

    if isinstance(human_decision, dict):
        approved = human_decision.get(
            "approved",
            False,
        )
    else:
        approved = bool(
            human_decision
        )

    if approved:
        return {
            "action_authorized": True,
            "human_approval": "APPROVED",
            "requires_human": False,
            "status": "HUMAN_APPROVED",
        }

    return {
        "action_authorized": False,
        "human_approval": "REJECTED",
        "status": "HUMAN_REJECTED",
    }