from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.actions import (
    determine_action,
    execute_action,
    request_human_approval,
)
from app.graph.customer_response import customer_response_node
from app.graph.nodes import investigate_case
from app.graph.resolution import resolution_controller
from app.graph.routing import (
    route_after_action,
    route_after_action_decision,
    route_after_human_approval,
    route_after_recovery,
    route_after_resolution,
    route_after_validation,
    route_case,
)
from app.graph.state import CaseState
from app.graph.validation import validate_resolution
from app.graph.nodes import authorization_gate

MAX_RECOVERY_ATTEMPTS = 3


def human_escalation(state: CaseState) -> dict[str, Any]:
    return {
        "requires_human": True,
        "case_completed": False,
        "resolution_success": False,
        "status": "HUMAN_ESCALATION",
        "resolution_failure_reason": state.get(
            "resolution_failure_reason",
            "The case could not be safely resolved automatically.",
        ),
    }


def recovery_node(state: CaseState) -> dict[str, Any]:
    attempts = int(state.get("recovery_attempts", 0) or 0) + 1
    if attempts > MAX_RECOVERY_ATTEMPTS:
        return {
            "recovery_attempts": attempts,
            "requires_human": True,
            "status": "HUMAN_ESCALATION",
            "resolution_failure_reason": "The maximum recovery attempts was reached.",
        }
    result = state.get("action_result", {}) or {}
    updates: dict[str, Any] = {
        "recovery_attempts": attempts,
        "resolution_success": False,
        "case_completed": False,
        "status": "RECOVERY_REPLANNING",
    }
    if result.get("replan") and result.get("next_domain"):
        updates["next_domain"] = result["next_domain"]
    return updates


def route_after_authorization(state: CaseState) -> str:
    status = str(state.get("status") or "")
    if status in {"WAITING_FOR_TRANSACTION_INFORMATION", "HUMAN_ESCALATION"}:
        return "customer_response" if status == "WAITING_FOR_TRANSACTION_INFORMATION" else "human_escalation"
    return "resolution_controller"


def build_casepilot_graph():
    builder = StateGraph(CaseState)
    builder.add_node("route_case", route_case)
    builder.add_node("investigate_case", investigate_case)
    builder.add_node("resolution_controller", resolution_controller)
    builder.add_node("validate_resolution", validate_resolution)
    builder.add_node("determine_action", determine_action)
    builder.add_node("authorization_gate", authorization_gate)
    builder.add_node("human_approval", request_human_approval)
    builder.add_node("execute_action", execute_action)
    builder.add_node("recovery", recovery_node)
    builder.add_node("human_escalation", human_escalation)
    builder.add_node("customer_response", customer_response_node)

    builder.add_edge(START, "route_case")
    builder.add_edge("route_case", "investigate_case")
    builder.add_edge("investigate_case", "resolution_controller")

    builder.add_conditional_edges(
        "resolution_controller",
        route_after_resolution,
        {
            "validate_resolution": "validate_resolution",
            "resolution_controller": "resolution_controller",
            "human_escalation": "human_escalation",
        },
    )
    builder.add_conditional_edges(
        "validate_resolution",
        route_after_validation,
        {
            "route_case": "route_case",
            "determine_action": "determine_action",
            "resolution_controller": "resolution_controller",
            "human_escalation": "human_escalation",
            "customer_response": "customer_response",
        },
    )
    builder.add_edge("determine_action", "authorization_gate")
    builder.add_conditional_edges(
        "authorization_gate",
        route_after_action_decision,
        {
            "human_approval": "human_approval",
            "execute_action": "execute_action",
            "customer_response": "customer_response",
            "human_escalation": "human_escalation",
        },
    )
    builder.add_conditional_edges(
        "human_approval",
        route_after_human_approval,
        {
            "execute_action": "execute_action",
            "customer_response": "customer_response",
        },
    )
    builder.add_conditional_edges(
        "execute_action",
        route_after_action,
        {
            "validate_resolution": "validate_resolution",
            "route_case": "route_case",
            "recovery": "recovery",
        },
    )
    builder.add_conditional_edges(
        "recovery",
        route_after_recovery,
        {
            "route_case": "route_case",
            "resolution_controller": "resolution_controller",
            "human_escalation": "human_escalation",
        },
    )
    builder.add_edge("human_escalation", "customer_response")
    builder.add_edge("customer_response", END)
    return builder.compile(checkpointer=MemorySaver())


casepilot_graph = build_casepilot_graph()
