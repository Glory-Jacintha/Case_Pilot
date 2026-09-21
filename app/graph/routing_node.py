from __future__ import annotations

from .router import route_customer_message
from .state import CaseState


def route_case(state: CaseState) -> dict:
    """
    Route the customer's current message into one CasePilot domain.
    """

    customer_message = state["customer_message"]

    decision = route_customer_message(customer_message)

    return {
        "domain": decision.domain,
        "issue_type": decision.issue_type,
        "domain_confidence": decision.confidence,
        "routing_reason": decision.reasoning,
        "reroute_count": state.get("reroute_count", 0),
    }