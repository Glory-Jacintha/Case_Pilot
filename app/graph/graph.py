from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    authorization_gate,
    investigate_case,
)
from app.graph.state import CaseState


def build_casepilot_graph():

    builder = StateGraph(CaseState)

    builder.add_node(
        "investigate_case",
        investigate_case,
    )

    builder.add_node(
        "authorization_gate",
        authorization_gate,
    )

    builder.add_edge(
        START,
        "investigate_case",
    )

    builder.add_edge(
        "investigate_case",
        "authorization_gate",
    )

    builder.add_edge(
        "authorization_gate",
        END,
    )

    # -------------------------------------------------
    # Development checkpointer
    # -------------------------------------------------

    checkpointer = MemorySaver()

    return builder.compile(
        checkpointer=checkpointer,
    )


casepilot_graph = build_casepilot_graph()