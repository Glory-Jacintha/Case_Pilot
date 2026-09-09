from __future__ import annotations

import re

from app.graph.state import CaseState
from app.agents.agent import casepilot_agent


HUMAN_APPROVAL_THRESHOLD = 2000.0


def investigate_case(state: CaseState) -> CaseState:
    """
    Ask the CasePilot agent to investigate the customer's issue
    using read-only tools.
    """

    customer_message = state.get("customer_message", "").strip()

    if not customer_message:
        return {
            "status": "INVESTIGATION_FAILED",
            "investigation": "No customer message was provided.",
        }

    result = casepilot_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": customer_message,
                }
            ]
        }
    )

    messages = result.get("messages", [])

    if not messages:
        return {
            "status": "INVESTIGATION_FAILED",
            "investigation": "The agent returned no messages.",
        }

    final_message = messages[-1]
    content = final_message.content

    # Gemini can return either a string or a list of content blocks.
    if isinstance(content, list):
        text_parts = []

        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        investigation_text = "\n".join(text_parts)
    else:
        investigation_text = str(content)

    # Look for the transaction amount reported by the agent.
    amount_match = re.search(
        r"TRANSACTION_AMOUNT\s*:\s*₹?\s*([0-9]+(?:\.[0-9]+)?)",
        investigation_text,
        re.IGNORECASE,
    )

    if not amount_match:
        return {
            "investigation": investigation_text,
            "status": "INVESTIGATION_AMOUNT_NOT_FOUND",
        }

    amount = float(amount_match.group(1))

    return {
        "investigation": investigation_text,
        "transaction_amount": amount,
        "status": "INVESTIGATION_COMPLETED",
    }


def authorization_gate(state: CaseState) -> CaseState:
    """
    Deterministic business authorization gate.

    >= ₹2,000  -> Human approval
    < ₹2,000   -> AI can proceed
    """

    amount = float(state.get("transaction_amount", 0.0))

    if amount >= HUMAN_APPROVAL_THRESHOLD:
        return {
            "authorization": "HUMAN_REQUIRED",
            "requires_human": True,
            "status": "WAITING_FOR_HUMAN_APPROVAL",
        }

    return {
        "authorization": "AI_ALLOWED",
        "requires_human": False,
        "status": "AI_CAN_PROCEED",
    }