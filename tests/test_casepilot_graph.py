from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import authorization_gate
from app.graph.resolution import resolution_controller
from app.graph.validation import validate_resolution
from app.graph.customer_response import customer_response_node
from app.graph.state import CaseState

from app.graph.graph import (
    human_escalation,
    route_after_authorization,
    route_after_resolution,
    route_after_validation,
)


def fake_investigate_case(state: CaseState) -> dict:
    """
    Fake investigation node.

    Used only for testing the deterministic LangGraph workflow
    without making a Gemini API request.
    """

    return {
        "investigation": (
            "Customer requested a refund for order ORD0000001. "
            "The order amount is ₹1999.00."
        ),
        "transaction_amount": 1999.0,
        "order_id": "ORD0000001",
        "issue_type": "REFUND",
        "status": "INVESTIGATION_COMPLETED",
        "requires_human": False,
    }


def build_test_graph():

    builder = StateGraph(CaseState)

    # Nodes
    builder.add_node(
        "investigate_case",
        fake_investigate_case,
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
        "human_escalation",
        human_escalation,
    )

    builder.add_node(
        "customer_response",
        customer_response_node,
    )

    # Initial flow
    builder.add_edge(
        START,
        "investigate_case",
    )

    builder.add_edge(
        "investigate_case",
        "authorization_gate",
    )

    # Authorization routing
    builder.add_conditional_edges(
        "authorization_gate",
        route_after_authorization,
        {
            "resolution_controller": "resolution_controller",
            "customer_response": "customer_response",
        },
    )

    # Resolution routing
    builder.add_conditional_edges(
        "resolution_controller",
        route_after_resolution,
        {
            "validate_resolution": "validate_resolution",
            "resolution_controller": "resolution_controller",
            "human_escalation": "human_escalation",
        },
    )

    # Validation routing
    builder.add_conditional_edges(
        "validate_resolution",
        route_after_validation,
        {
            "customer_response": "customer_response",
            "resolution_controller": "resolution_controller",
            "human_escalation": "human_escalation",
        },
    )

    # Human escalation
    builder.add_edge(
        "human_escalation",
        "customer_response",
    )

    # Final response
    builder.add_edge(
        "customer_response",
        END,
    )

    return builder.compile(
        checkpointer=MemorySaver(),
    )


def test_casepilot_graph_low_value_refund():

    test_graph = build_test_graph()

    result = test_graph.invoke(
        {
            "session_id": "test-session-001",
            "customer_message": (
                "I want a refund for my order ORD0000001"
            ),
            "conversation_history": [
                {
                    "role": "user",
                    "content": (
                        "I want a refund for my order ORD0000001"
                    ),
                }
            ],
        },
        config={
            "configurable": {
                "thread_id": "test-session-001",
            }
        },
    )

    print("\n========== CASEPILOT RESULT ==========")
    print("Status:", result.get("status"))
    print("Amount:", result.get("transaction_amount"))
    print("Authorization:", result.get("authorization"))
    print("Requires human:", result.get("requires_human"))
    print("Current strategy:", result.get("current_strategy"))
    print("Attempted strategies:", result.get("attempted_strategies"))
    print("Resolution success:", result.get("resolution_success"))
    print("Resolution result:", result.get("resolution_result"))
    print("Customer response:", result.get("customer_response"))

    assert result.get("transaction_amount") == 1999.0
    assert result.get("authorization") == "AI_ALLOWED"