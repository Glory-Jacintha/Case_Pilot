from __future__ import annotations

import json

from langchain_google_genai import ChatGoogleGenerativeAI

from app.graph.state import CaseState


model = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    max_retries=3,
)


CUSTOMER_RESPONSE_PROMPT = """
You are CasePilot, an e-commerce customer support assistant.

Your job is to write the FINAL response that will be shown directly
to the customer.

You will receive structured internal case information.

IMPORTANT RULES:

1. Never expose internal implementation details.
2. Never mention:
   - internal strategy names
   - strategy numbers
   - internal error codes
   - authorization flags
   - LangGraph
   - tools
   - databases
   - internal investigation
   - system state
   - internal transaction metadata
3. Never invent an action that the system did not actually complete.
4. Never claim a refund was completed if the action result does not
   confirm it.
5. If human approval is required, clearly tell the customer that
   their request has been sent for human review.
6. If the request could not be resolved automatically, explain that
   a support specialist will continue the case.
7. If information is missing, politely ask only for the information
   required to continue.
8. Be concise, natural, professional, and helpful.
9. Speak directly to the customer.
10. Do not mention that you are an AI unless necessary.

Generate ONLY the customer-facing response.
Do not add headings such as "Response:".
"""


def _safe_customer_state(state: CaseState) -> dict:
    """
    Build a restricted representation of internal state.

    Only information that may help Gemini formulate the customer
    response is passed to the model.
    """

    return {
        "customer_message": state.get("customer_message", ""),
        "domain": state.get("domain", ""),
        "issue_type": state.get("issue_type", ""),
        "order_id": state.get("order_id", ""),
        "transaction_amount": state.get("transaction_amount"),
        "status": state.get("status", ""),
        "resolution_success": state.get(
            "resolution_success",
            False,
        ),
        "resolution_result": state.get(
            "resolution_result",
            {},
        ),
        "action_result": state.get(
            "action_result",
            {},
        ),
        "requires_human": state.get(
            "requires_human",
            False,
        ),
        "human_approval": state.get(
            "human_approval",
            "",
        ),
        "resolution_failure_reason": state.get(
            "resolution_failure_reason",
            "",
        ),
    }


def customer_response_node(state: CaseState) -> dict:
    """
    Generate the final customer-facing response using Gemini.

    Internal CasePilot state is converted into a restricted,
    customer-safe representation before being sent to the LLM.
    """

    safe_state = _safe_customer_state(state)

    prompt = (
        CUSTOMER_RESPONSE_PROMPT
        + "\n\nINTERNAL CASE RESULT:\n"
        + json.dumps(
            safe_state,
            indent=2,
            default=str,
        )
    )

    response = model.invoke(prompt)

    content = response.content

    if isinstance(content, list):
        text_parts = []

        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text_parts.append(
                        block.get("text", "")
                    )

        message = "\n".join(text_parts).strip()

    else:
        message = str(content).strip()

    if not message:
        message = (
            "I've checked your request, but I need "
            "a little more information before I can continue."
        )

    return {
        "customer_response": message,
        "status": _customer_status(state),
    }


def _customer_status(state: CaseState) -> str:
    """
    Convert internal statuses into customer-facing workflow statuses.
    """

    status = state.get("status", "")

    if status == "WAITING_FOR_HUMAN_APPROVAL":
        return "CUSTOMER_AWAITING_HUMAN"

    if status == "HUMAN_ESCALATION":
        return "CUSTOMER_ESCALATED"

    if status == "AWAITING_TRANSACTION_INFORMATION":
        return "CUSTOMER_NEEDS_INFORMATION"

    if status == "INVESTIGATION_FAILED":
        return "CUSTOMER_NEEDS_INFORMATION"

    if state.get("resolution_success"):
        return "RESOLUTION_COMPLETED"

    if state.get("action_result", {}).get("success"):
        return "RESOLUTION_COMPLETED"

    return "CUSTOMER_RESPONSE_READY"