from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from app.graph.state import CaseState
from app.graph.nodes import (
    investigate_case,
    authorization_gate,
)


def build_casepilot_graph():
    builder = StateGraph(CaseState)

    builder.add_node("investigate_case", investigate_case)
    builder.add_node("authorization_gate", authorization_gate)

    builder.add_edge(START, "investigate_case")
    builder.add_edge("investigate_case", "authorization_gate")
    builder.add_edge("authorization_gate", END)

    return builder.compile()


casepilot_graph = build_casepilot_graph()