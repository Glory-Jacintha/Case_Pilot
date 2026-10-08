from __future__ import annotations

import re
import uuid
from typing import Any

SUPPORTED_DOMAINS = {
    "ORDER",
    "PAYMENT",
    "DELIVERY",
    "REFUND",
    "RETURN",
    "CANCELLATION",
    "PRODUCT_QUERY",
}
MAX_DOMAIN_TRANSITIONS = 10


def _detect_domain(message: str, current: str | None) -> tuple[str | None, str]:
    text = message.lower().strip()
    cancellation_dispute = (
        "i didn't cancel",
        "i did not cancel",
        "i haven't cancelled",
        "i have not cancelled",
        "i never cancelled",
        "wasn't me",
        "was not me",
        "why was my order cancelled",
        "why did my order get cancelled",
        "why is my order cancelled",
    )
    if any(phrase in text for phrase in cancellation_dispute):
        return (
            "ORDER",
            "The customer is disputing an unexpected cancellation.",
        )

    wants_cancel = any(
        word in text for word in ("cancel", "cancellation")
    )
    wants_return = any(
        word in text for word in ("return", "send it back")
    )
    wants_refund = any(
        word in text for word in ("refund", "money back", "moneyback")
    )

    # Preserve dependency order for multi-intent requests.
    if wants_cancel and wants_refund:
        return "CANCELLATION", "The customer requested cancellation followed by a refund."
    if wants_return and wants_refund:
        return "RETURN", "The customer requested a return followed by a refund."
    if wants_cancel:
        return "CANCELLATION", "Current customer message requests cancellation."
    if wants_return:
        return "RETURN", "Current customer message requests a return."
    if wants_refund:
        return "REFUND", "Current customer message requests or asks about a refund."

    rules = [
        (
            "DELIVERY",
            (
                "delivery",
                "delivered",
                "package",
                "parcel",
                "tracking",
                "didn't receive",
                "did not receive",
                "not received",
                "haven't received",
                "have not received",
                "missing",
            ),
        ),
        (
            "PAYMENT",
            ("payment", "paid", "charged", "transaction"),
        ),
        (
            "PRODUCT_QUERY",
            (
                "product",
                "warranty",
                "specification",
                "features",
                "about this",
            ),
        ),
        ("ORDER", ("order", "status")),
    ]
    for domain, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return domain, f"Current customer message matches {domain} intent."
    return current, "No new domain signal; preserving the current routed domain."


def _entity_values(state: dict[str, Any], message: str) -> dict[str, str | None]:
    patterns = {
        "order_id": r"ORD[A-Z0-9]*[0-9][A-Z0-9]*",
        "customer_id": r"CUST[A-Z0-9]*[0-9][A-Z0-9]*",
        "product_id": r"(?:PROD|P)[A-Z0-9]*[0-9][A-Z0-9]*",
        "refund_id": r"REF[A-Z0-9]*[0-9][A-Z0-9]*",
    }
    values: dict[str, str | None] = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, message, re.IGNORECASE)
        values[field] = match.group(0).upper() if match else None
    return values


def _has_new_explicit_entity(state: dict[str, Any], message: str) -> bool:
    values = _entity_values(state, message)
    for field, value in values.items():
        if value and value != str(state.get(field) or "").upper():
            return True
    return False


def _reset_resolution_context() -> dict[str, Any]:
    return {
        "current_strategy": "",
        "attempted_strategies": [],
        "resolution_attempts": [],
        "recovery_attempts": 0,
        "resolution_result": {},
        "resolution_success": False,
        "resolution_failure_reason": "",
        "action_required": False,
        "action_ready": False,
        "action_type": "",
        "action_reason": "",
        "action_key": "",
        "action_result": {},
        "action_authorized": False,
        "requires_human": False,
        "authorization": "PENDING",
        "authorization_reason": "",
        "human_approval": "",
        "approval_reason": "",
        "human_approval_threshold": None,
        "pending_authorization_action": None,
        "transaction_amount": None,
        "transaction_currency": None,
        "transaction_amount_status": "UNKNOWN",
        "case_completed": False,
        "partially_completed": False,
        "replan_required": False,
        "pending_information": [],
    }


def _new_case_id(session_id: str) -> str:
    return f"{session_id}:{uuid.uuid4().hex[:12]}"


def route_case(state: dict[str, Any]) -> dict[str, Any]:
    requested = str(state.get("next_domain") or "").upper().strip()
    current = str(state.get("domain") or "").upper().strip() or None
    message = str(state.get("customer_message") or "").strip()
    entity_values = _entity_values(state, message)
    new_entity = _has_new_explicit_entity(state, message)

    customer_domain, customer_reason = _detect_domain(message, current)
    if requested in SUPPORTED_DOMAINS and requested != current:
        new_domain = requested
        reason = f"Workflow dependency requires transition to {requested}."
        transition_type = "REPLAN"
    else:
        new_domain = customer_domain
        reason = customer_reason
        transition_type = "CUSTOMER_ROUTING" if new_domain != current else "NO_CHANGE"

    if not new_domain:
        return {
            "status": "ROUTING_FAILED",
            "routing_reason": "The customer request could not be mapped to a supported domain.",
            "resolution_failure_reason": "A supported customer-support domain could not be determined.",
        }

    history = list(state.get("domain_history") or [])
    visited = list(state.get("visited_domains") or [])
    case_id = str(state.get("case_id") or "")

    # A new operational identifier starts a new case. Conversation history
    # remains available globally, but operational workflow state is isolated.
    new_case = new_entity and bool(case_id)
    if not case_id:
        new_case = True
        case_id = _new_case_id(str(state.get("session_id") or "session"))

    if new_case:
        history = []
        visited = []

    transitions = len(history)
    if new_domain != current:
        if transitions >= MAX_DOMAIN_TRANSITIONS:
            return {
                "status": "HUMAN_ESCALATION",
                "requires_human": True,
                "resolution_failure_reason": "The maximum number of domain transitions was reached; further automatic rerouting is blocked for safety.",
            }
        history.append({
            "from_domain": current,
            "to_domain": new_domain,
            "reason": reason,
            "trigger": transition_type,
            "validated": False,
        })

    if new_domain not in visited:
        visited.append(new_domain)

    updates: dict[str, Any] = {
        "case_id": case_id,
        "domain": new_domain,
        "issue_type": new_domain,
        "routing_reason": reason,
        "domain_history": history,
        "visited_domains": visited,
        "reroute_count": len(history),
        "next_domain": None,
        "status": "ROUTED",
    }

    if entity_values["order_id"]:
        updates["order_id"] = entity_values["order_id"]
        updates["product_id"] = None
        updates["refund_id"] = None
    elif entity_values["product_id"]:
        updates["product_id"] = entity_values["product_id"]
        updates["order_id"] = None
        updates["refund_id"] = None
    elif entity_values["refund_id"]:
        updates["refund_id"] = entity_values["refund_id"]
        updates["order_id"] = None
        updates["product_id"] = None
    elif entity_values["customer_id"]:
        updates["customer_id"] = entity_values["customer_id"]
        updates["order_id"] = None
        updates["product_id"] = None
        updates["refund_id"] = None

    if entity_values["customer_id"]:
        updates["customer_id"] = entity_values["customer_id"]

    if new_domain != current or new_entity:
        updates.update(_reset_resolution_context())

    # Keep a case-scoped conversation separate from the full session history.
    case_history = list(state.get("case_conversation_history") or [])
    if new_case:
        case_history = []
    if message:
        if not case_history or case_history[-1].get("content") != message:
            case_history.append({"role": "user", "content": message})
    updates["case_conversation_history"] = case_history
    return updates


def _domain_attempts(state: dict[str, Any]) -> list[dict[str, Any]]:
    domain = str(state.get("domain") or "").upper()
    return [
        attempt
        for attempt in state.get("resolution_attempts", []) or []
        if str(attempt.get("domain") or "").upper() == domain
    ]


def route_after_resolution(state: dict[str, Any]) -> str:
    status = str(state.get("status") or "")
    if status == "HUMAN_ESCALATION":
        return "human_escalation"
    if status == "RESOLUTION_STRATEGY_FAILED":
        return "resolution_controller" if len(_domain_attempts(state)) < 3 else "human_escalation"
    return "validate_resolution"


def route_after_validation(state: dict[str, Any]) -> str:
    if state.get("next_domain") and state.get("next_domain") != state.get("domain"):
        return "route_case"
    if state.get("status") == "HUMAN_ESCALATION":
        return "human_escalation"
    if state.get("action_ready"):
        return "determine_action"
    if state.get("case_completed"):
        return "customer_response"
    if state.get("status") == "DOMAIN_REPLAN_REQUIRED":
        return "route_case"
    return "resolution_controller" if len(_domain_attempts(state)) < 3 else "human_escalation"


def route_after_action_decision(state: dict[str, Any]) -> str:
    status = str(state.get("status") or "")
    if status == "HUMAN_ESCALATION":
        return "human_escalation"
    if status == "WAITING_FOR_TRANSACTION_INFORMATION":
        return "customer_response"
    if state.get("action_required"):
        if state.get("requires_human") or state.get("authorization") == "HUMAN_REQUIRED":
            return "human_approval"
        return "execute_action"
    return "customer_response"


def route_after_human_approval(state: dict[str, Any]) -> str:
    if state.get("status") == "HUMAN_APPROVED" and state.get("action_authorized"):
        return "execute_action"
    return "customer_response"


def route_after_action(state: dict[str, Any]) -> str:
    result = state.get("action_result") or {}
    if result.get("success"):
        return "validate_resolution"
    if state.get("next_domain"):
        return "route_case"
    return "recovery"


def route_after_recovery(state: dict[str, Any]) -> str:
    if state.get("next_domain"):
        return "route_case"
    attempts = _domain_attempts(state)
    recovery_attempts = int(state.get("recovery_attempts", 0) or 0)
    if len(attempts) < 3 and recovery_attempts <= 3:
        return "resolution_controller"
    return "human_escalation"
