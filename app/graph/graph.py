from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    authorization_gate,
    investigate_case,
)
from app.graph.resolution import resolution_controller
from app.graph.validation import validate_resolution
from app.graph.customer_response import customer_response_node
from app.graph.state import CaseState


def human_escalation(state: CaseState) -> dict:
    """
    Prepare the case for human support when AI cannot safely
    complete the resolution.
    """

    return {
        "requires_human": True,
        "resolution_success": False,
        "status": "HUMAN_ESCALATION",
        "resolution_failure_reason": state.get(
            "resolution_failure_reason",
            "The available resolution strategies were unsuccessful.",
        ),
    }


def route_after_authorization(state: CaseState) -> str:
    """
    Decide whether the case can proceed automatically
    or needs human involvement.
    """

    if state.get("requires_human", False):
        return "customer_response"

    if state.get("status") == "AWAITING_TRANSACTION_INFORMATION":
        return "customer_response"

    return "resolution_controller"


def route_after_resolution(state: CaseState) -> str:
    """
    Decide what happens after a resolution strategy executes.
    """

    status = state.get("status", "")

    # Controller has already determined that all strategies
    # have been exhausted.
    if status == "HUMAN_ESCALATION":
        return "human_escalation"

    # Strategy failed. Try another strategy if available.
    if status == "RESOLUTION_STRATEGY_FAILED":
        attempted = state.get("attempted_strategies", [])

        if len(attempted) >= 3:
            return "human_escalation"

        return "resolution_controller"

    # Strategy executed successfully at tool level.
    # We must validate the actual business outcome.
    return "validate_resolution"


def route_after_validation(state: CaseState) -> str:
    """
    Decide whether validation completed the case or
    another resolution strategy should be attempted.
    """

    if state.get("resolution_success", False):
        return "customer_response"

    attempted = state.get("attempted_strategies", [])

    if len(attempted) >= 3:
        return "human_escalation"

    return "resolution_controller"


def build_casepilot_graph():
    builder = StateGraph(CaseState)

    # --------------------------------------------------
    # Nodes
    # --------------------------------------------------

    builder.add_node("investigate_case", investigate_case)
    builder.add_node("authorization_gate", authorization_gate)
    builder.add_node("resolution_controller", resolution_controller)
    builder.add_node("validate_resolution", validate_resolution)
    builder.add_node("human_escalation", human_escalation)
    builder.add_node("customer_response", customer_response_node)

    # --------------------------------------------------
    # Initial flow
    # --------------------------------------------------

    builder.add_edge(
        START,
        "investigate_case",
    )

    builder.add_edge(
        "investigate_case",
        "authorization_gate",
    )

    # --------------------------------------------------
    # Authorization routing
    # --------------------------------------------------

    builder.add_conditional_edges(
        "authorization_gate",
        route_after_authorization,
        {
            "resolution_controller": "resolution_controller",
            "customer_response": "customer_response",
        },
    )

    # --------------------------------------------------
    # Resolution → validation / escalation
    # --------------------------------------------------

    builder.add_conditional_edges(
        "resolution_controller",
        route_after_resolution,
        {
            "validate_resolution": "validate_resolution",
            "resolution_controller": "resolution_controller",
            "human_escalation": "human_escalation",
        },
    )

    # --------------------------------------------------
    # Validation → success / next strategy / human
    # --------------------------------------------------

    builder.add_conditional_edges(
        "validate_resolution",
        route_after_validation,
        {
            "customer_response": "customer_response",
            "resolution_controller": "resolution_controller",
            "human_escalation": "human_escalation",
        },
    )

    # --------------------------------------------------
    # End states
    # --------------------------------------------------

    builder.add_edge(
        "human_escalation",
        "customer_response",
    )

    builder.add_edge(
        "customer_response",
        END,
    )

    # --------------------------------------------------
    # Checkpointer
    # --------------------------------------------------

    checkpointer = MemorySaver()

    return builder.compile(
        checkpointer=checkpointer,
    )


casepilot_graph = build_casepilot_graph()