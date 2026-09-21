from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    authorization_gate,
    investigate_case,
)
from app.graph.routing_node import route_case
from app.graph.resolution import resolution_controller
from app.graph.validation import validate_resolution
from app.graph.action_controller import determine_action
from app.graph.action_executor import execute_action
from app.graph.human_approval import request_human_approval
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
    Decide whether the case can proceed through resolution
    or requires human transaction approval.
    """

    if state.get("status") == "AWAITING_TRANSACTION_INFORMATION":
        return "customer_response"

    # Important:
    # Human-required cases still need to go through resolution
    # so that the system can gather evidence before asking for
    # approval.
    return "resolution_controller"


def route_after_resolution(state: CaseState) -> str:
    """
    Decide what happens after a resolution strategy executes.
    """

    status = state.get("status", "")

    if status == "HUMAN_ESCALATION":
        return "human_escalation"

    if status == "RESOLUTION_STRATEGY_FAILED":
        attempted = state.get(
            "attempted_strategies",
            [],
        )

        if len(attempted) >= 3:
            return "human_escalation"

        return "resolution_controller"

    return "validate_resolution"


def route_after_validation(state):

    # --------------------------------------------------------
    # POST-ACTION VALIDATION
    # --------------------------------------------------------
    #
    # If an action was successfully executed and validation
    # confirms the final state, do NOT go back to
    # determine_action.
    #
    # Otherwise the same transaction would execute twice.
    # --------------------------------------------------------

    action_result = state.get(
        "action_result",
        {},
    )

    if (
        isinstance(action_result, dict)
        and action_result.get("success") is True
        and state.get("resolution_success", False)
    ):
        return "customer_response"

    # --------------------------------------------------------
    # PRE-ACTION ELIGIBILITY
    # --------------------------------------------------------
    #
    # Example:
    #
    # REFUND_ELIGIBILITY_REVIEW
    #         ↓
    # ACTION_READY
    #         ↓
    # determine_action
    #
    # No transaction has happened yet.
    # --------------------------------------------------------

    if state.get(
        "action_ready",
        False,
    ):
        return "determine_action"

    # --------------------------------------------------------
    # Successful investigation-only resolution
    #
    # Example:
    #
    # ORDER
    # PAYMENT
    # DELIVERY
    # PRODUCT_QUERY
    #
    # These domains don't necessarily require a transaction.
    # --------------------------------------------------------

    if state.get(
        "resolution_success",
        False,
    ):
        return "determine_action"

    # --------------------------------------------------------
    # Validation failed
    #
    # Give the resolution controller another opportunity if
    # fewer than three strategies have been attempted.
    # --------------------------------------------------------

    attempted = state.get(
        "attempted_strategies",
        [],
    )

    if len(attempted) >= 3:
        return "human_escalation"

    return "resolution_controller"


def route_after_action_decision(state: CaseState) -> str:
    """
    Decide whether the case needs a write action.
    """

    if state.get("action_required", False):
        if state.get("requires_human", False):
            return "human_approval"

        return "execute_action"

    return "customer_response"


def route_after_human_approval(state: CaseState) -> str:
    """
    Decide what happens after human approval/rejection.
    """

    status = state.get("status", "")

    if status == "HUMAN_APPROVED":
        return "execute_action"

    return "customer_response"


def route_after_action(state: CaseState) -> str:
    """
    Decide what happens after an action is executed.
    """

    action_result = state.get(
        "action_result",
        {},
    )

    if action_result.get("success"):
        return "validate_resolution"

    return "customer_response"


def build_casepilot_graph():
    builder = StateGraph(CaseState)

    # --------------------------------------------------
    # Nodes
    # --------------------------------------------------

    builder.add_node(
        "route_case",
        route_case,
    )

    builder.add_node(
        "investigate_case",
        investigate_case,
    )

    builder.add_node(
        "authorization_gate",
        authorization_gate,
    )

    builder.add_node(
        "resolution_controller",
        resolution_controller,
    )

    builder.add_node(
        "validate_resolution",
        validate_resolution,
    )

    builder.add_node(
        "determine_action",
        determine_action,
    )

    builder.add_node(
        "human_approval",
        request_human_approval,
    )

    builder.add_node(
        "execute_action",
        execute_action,
    )

    builder.add_node(
        "human_escalation",
        human_escalation,
    )

    builder.add_node(
        "customer_response",
        customer_response_node,
    )

    # --------------------------------------------------
    # Initial flow
    # --------------------------------------------------

    builder.add_edge(
        START,
        "route_case",
    )

    builder.add_edge(
        "route_case",
        "investigate_case",
    )

    builder.add_edge(
        "investigate_case",
        "authorization_gate",
    )

    # --------------------------------------------------
    # Authorization
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
    # Resolution
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
    # Validation
    # --------------------------------------------------

    builder.add_conditional_edges(
        "validate_resolution",
        route_after_validation,
        {
            "determine_action": "determine_action",
            "resolution_controller": "resolution_controller",
            "human_escalation": "human_escalation",
            "customer_response": "customer_response",
        },
    )

    # --------------------------------------------------
    # Action decision
    # --------------------------------------------------

    builder.add_conditional_edges(
        "determine_action",
        route_after_action_decision,
        {
            "human_approval": "human_approval",
            "execute_action": "execute_action",
            "customer_response": "customer_response",
        },
    )

    # --------------------------------------------------
    # Human approval
    # --------------------------------------------------

    builder.add_conditional_edges(
        "human_approval",
        route_after_human_approval,
        {
            "execute_action": "execute_action",
            "customer_response": "customer_response",
        },
    )

    # --------------------------------------------------
    # Action execution
    # --------------------------------------------------

    builder.add_conditional_edges(
        "execute_action",
        route_after_action,
        {
            "validate_resolution": "validate_resolution",
            "customer_response": "customer_response",
        },
    )

    # --------------------------------------------------
    # Human escalation
    # --------------------------------------------------

    builder.add_edge(
        "human_escalation",
        "customer_response",
    )

    # --------------------------------------------------
    # Final response
    # --------------------------------------------------

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