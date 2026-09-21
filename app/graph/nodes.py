from __future__ import annotations

import re

from app.agents.agent import casepilot_agent
from app.graph.state import CaseState


HUMAN_APPROVAL_THRESHOLD = 2000.0


def _extract_text(content) -> str:
    """Convert an LLM response into plain text."""

    if isinstance(content, list):
        text_parts = []

        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        return "\n".join(text_parts)

    return str(content)


def _extract_order_id(text: str) -> str | None:
    """Extract an order ID such as ORD0000001."""

    match = re.search(
        r"\bORD\d{7,}\b",
        text,
        re.IGNORECASE,
    )

    return match.group(0).upper() if match else None


def _extract_customer_id(text: str) -> str | None:
    """Extract a customer ID such as CUST0000001."""

    match = re.search(
        r"\bCUST\d{7,}\b",
        text,
        re.IGNORECASE,
    )

    return match.group(0).upper() if match else None


def _extract_product_id(text: str) -> str | None:
    """Extract a product ID such as PROD0000001."""

    match = re.search(
        r"\bPROD\d{7,}\b",
        text,
        re.IGNORECASE,
    )

    return match.group(0).upper() if match else None


def investigate_case(state: CaseState) -> CaseState:
    """
    Investigate the customer issue while preserving
    the conversation history.
    """

    customer_message = state.get(
        "customer_message",
        "",
    ).strip()

    if not customer_message:
        return {
            "status": "INVESTIGATION_FAILED",
            "investigation": "No customer message was provided.",
        }

    # -------------------------------------------------
    # Build conversation for the agent
    # -------------------------------------------------

    history = state.get(
        "conversation_history",
        [],
    )

    agent_messages = [
        {
            "role": message["role"],
            "content": message["content"],
        }
        for message in history
    ]

    # -------------------------------------------------
    # Ask CasePilot agent
    # -------------------------------------------------

    result = casepilot_agent.invoke(
        {
            "messages": agent_messages,
        }
    )

    messages = result.get("messages", [])

    if not messages:
        return {
            "status": "INVESTIGATION_FAILED",
            "investigation": "The agent returned no messages.",
        }

    final_message = messages[-1]

    investigation_text = _extract_text(
        final_message.content
    )

    # -------------------------------------------------
    # Extract transaction amount
    # -------------------------------------------------

    amount_match = re.search(
        r"TRANSACTION_AMOUNT\s*:\s*₹?\s*([0-9]+(?:\.[0-9]+)?)",
        investigation_text,
        re.IGNORECASE,
    )

    # -------------------------------------------------
    # Initial state updates
    # -------------------------------------------------

    updates: CaseState = {
        "investigation": investigation_text,
        "status": "INVESTIGATION_COMPLETED",
    }

    # -------------------------------------------------
    # Extract identifiers
    #
    # Search both the original customer message and
    # the investigation result.
    # -------------------------------------------------

    combined_text = (
        customer_message
        + "\n"
        + investigation_text
    )

    order_id = _extract_order_id(
        combined_text
    )

    customer_id = _extract_customer_id(
        combined_text
    )

    product_id = _extract_product_id(
        combined_text
    )

    if order_id:
        updates["order_id"] = order_id

    if customer_id:
        updates["customer_id"] = customer_id

    if product_id:
        updates["product_id"] = product_id

    if amount_match:
        updates["transaction_amount"] = float(
            amount_match.group(1)
        )

    # -------------------------------------------------
    # Preserve conversation history
    # -------------------------------------------------

    updates["conversation_history"] = [
        {
            "role": "assistant",
            "content": investigation_text,
        }
    ]

    return updates


def authorization_gate(state: CaseState) -> CaseState:
    """
    Deterministic business authorization gate.

    < ₹2,000  -> AI allowed
    ≥ ₹2,000  -> Human required

    If the transaction amount is not known yet,
    we do NOT authorize a transaction.
    """

    amount = state.get(
        "transaction_amount"
    )

    # -------------------------------------------------
    # Transaction amount is unknown
    # -------------------------------------------------

    if amount is None:
        return {
            "status": "AWAITING_TRANSACTION_INFORMATION",
            "requires_human": False,
        }

    amount = float(amount)

    # -------------------------------------------------
    # Human approval threshold
    # -------------------------------------------------

    if amount >= HUMAN_APPROVAL_THRESHOLD:
        return {
            "authorization": "HUMAN_REQUIRED",
            "requires_human": True,
            "status": "WAITING_FOR_HUMAN_APPROVAL",
        }

    # -------------------------------------------------
    # AI allowed
    # -------------------------------------------------

    return {
        "authorization": "AI_ALLOWED",
        "requires_human": False,
        "status": "AI_CAN_PROCEED",
    }