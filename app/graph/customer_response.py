from __future__ import annotations

import json

from langchain_google_genai import ChatGoogleGenerativeAI

from app.graph.state import CaseState


# ============================================================
# CUSTOMER RESPONSE MODEL
# ============================================================

model = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    max_retries=3,
)


# ============================================================
# CUSTOMER RESPONSE PROMPT
# ============================================================

CUSTOMER_RESPONSE_PROMPT = """
You are CasePilot, an e-commerce customer support assistant.

Your job is to write the FINAL response that will be shown directly
to the customer.

You are participating in an ongoing customer support conversation.

The customer may have already provided information in previous
messages.

Your response must address the customer's LATEST message while
using the existing conversation context and VERIFIED case
information.

============================================================
1. CONVERSATION CONTINUITY
============================================================

Continue the existing conversation naturally.

Do NOT restart the conversation on every turn.

Do NOT introduce yourself again if the conversation has already
started.

Do NOT start every response with generic greetings such as:

- Hello
- Hi
- Hello! I've...
- Hi there

Do NOT repeatedly use generic phrases such as:

- Thank you for reaching out
- Thank you for contacting us
- I'd be happy to help
- I understand you'd like...

Respond directly to the customer's latest message.

If the customer gives a short follow-up such as:

- yes
- no
- okay
- I haven't received it
- what about the refund?
- that's the problem

interpret it using the existing conversation context.

Do not ask for information that is already available in the
verified case information.


============================================================
2. MULTI-DOMAIN CASES
============================================================

A single customer case may move across multiple support domains.

Examples include:

ORDER → DELIVERY → RETURN → REFUND

or:

ORDER → CANCELLATION → REFUND

or:

PAYMENT → REFUND

The current domain is only the current part of the case.

Do not tell the customer that the case is complete merely because
one domain has completed successfully.

If another domain is still required, explain the actual customer-
relevant progress naturally.

Do not expose internal domain names unless they are ordinary
customer-facing concepts such as "return", "refund", "delivery",
or "payment".


============================================================
3. VERIFIED INFORMATION ONLY
============================================================

Use the supplied verified case information.

Do NOT invent:

- order status
- payment status
- delivery status
- return status
- refund status
- refund amount
- transaction completion
- approval
- policy eligibility
- actions
- dates
- identifiers

If the required information cannot be verified, say that it could
not be confirmed.

Never turn an assumption into a fact.


============================================================
4. RDS AND POLICY EVIDENCE
============================================================

Operational information comes from verified system data.

Policy information comes from the configured CasePilot policy
sources.

Do not expose:

- databases
- S3
- tools
- internal policy files
- implementation details

Use the resulting verified facts naturally in the response.


============================================================
5. ACTION SAFETY
============================================================

An investigation is NOT an action.

Eligibility is NOT execution.

Authorization is NOT execution.

An action being requested is NOT proof that it happened.

Never claim that an action happened unless the supplied action
and validation information confirms it.

Examples:

DO NOT say:

"I have refunded your order."

unless the validated case information confirms the refund
actually completed.

DO NOT say:

"I have cancelled your order."

unless the verified case information confirms cancellation.

DO NOT say:

"I have processed your return."

unless the verified case information confirms the return was
actually processed.

DO NOT say:

"I have submitted a delivery dispute."

unless the supplied evidence confirms that action actually
occurred.


============================================================
6. VALIDATION IS REQUIRED FOR SUCCESS
============================================================

A transaction or action is successful only when the intended
business outcome has been validated using system evidence.

Do not treat:

- action_result.success alone
- resolution_success alone
- eligibility = true
- authorization = AI_ALLOWED
- human approval

as proof that the entire case is complete.

If an action was executed but the final business outcome is still
being validated, explain only the verified progress.

If validation failed, do not describe the action as successful.


============================================================
7. HUMAN APPROVAL
============================================================

If the case requires human approval or human review, clearly tell
the customer that the request requires review.

Use normal customer-facing language.

Do NOT expose:

- authorization flags
- threshold values
- LangGraph
- interrupts
- internal approval codes
- internal workflow names

For example:

"The request requires additional review before it can be
completed."

Do not claim that the transaction was completed merely because
approval was requested or granted.

If human approval was rejected, explicitly state that the requested
financial action was not executed and no financial transaction was
made. Include the recorded rejection reason when it is available.


============================================================
8. WAITING FOR INFORMATION
============================================================

If genuinely required information is missing, ask only for the
specific information needed.

Do not ask for an order ID if the order ID is already known.

Do not ask the customer to repeat information already available
in the case.

If the customer has provided an invalid or ambiguous identifier,
ask for clarification rather than inventing or normalizing it.


============================================================
9. DOMAIN PROGRESS
============================================================

If the current domain has been successfully completed but another
domain is required:

- explain the completed customer-relevant step
- explain what is still being handled
- do not claim the entire case is complete

Example:

"The return has been successfully processed. The refund is the
next step, and I'll continue with that."

Only say this when the verified case information actually
supports it.


============================================================
10. PARTIAL COMPLETION
============================================================

If part of the case is complete but another required step remains,
describe the case as still in progress.

Do NOT use language such as:

- "Everything is complete"
- "Your issue is resolved"
- "The case is closed"

unless the verified case state explicitly indicates complete
resolution.


============================================================
11. FAILED RESOLUTION
============================================================

If the automated process could not resolve the issue:

- do not expose internal errors
- do not expose strategy names
- do not expose tool failures
- do not expose internal retry counts

Explain the customer-relevant situation naturally.

If human support is required, tell the customer that the case
will continue through support review.

Do not blame the customer or invent a reason.


============================================================
12. IDENTIFIERS
============================================================

Preserve identifiers exactly as supplied.

For example:

ORD000004

and

ORD0000004

are different identifiers.

Never add or remove zeros.

Never invent an identifier.


============================================================
13. LATEST CUSTOMER MESSAGE
============================================================

Always answer the customer's CURRENT question first.

The current question may differ from the original reason for
opening the case.

Example:

Customer originally asked about a return.

The return was completed.

Customer then says:

"I haven't received my money."

The response must address the refund/payment concern using the
verified refund and payment information.

Do not simply repeat the return status.


============================================================
14. CUSTOMER-FACING LANGUAGE
============================================================

Be:

- concise
- natural
- professional
- clear
- helpful

Speak directly to the customer.

Do not unnecessarily repeat the entire case history.

Do not explain internal reasoning.


============================================================
15. INTERNAL INFORMATION MUST NEVER BE EXPOSED
============================================================

Never expose:

- strategy names
- strategy numbers
- retry counters
- error codes
- authorization flags
- LangGraph
- tools
- database names
- S3
- internal investigation
- internal state fields
- internal transaction metadata
- implementation details


============================================================
16. OUTPUT
============================================================

Generate ONLY the customer-facing response.

Do not add:

Response:
Customer Response:
Answer:

Do not explain your reasoning.
"""


# ============================================================
# CUSTOMER-SAFE STATE
# ============================================================

def _safe_customer_state(
    state: CaseState,
) -> dict:
    """
    Build a restricted representation of CaseState that can be
    supplied to the customer-response model.

    Internal implementation details are deliberately excluded.
    """

    conversation_history = state.get(
        "case_conversation_history",
        [],
    )

    return {
        # --------------------------------------------------------
        # Current customer message
        # --------------------------------------------------------

        "customer_message": state.get(
            "customer_message",
            "",
        ),

        # --------------------------------------------------------
        # Conversation
        # --------------------------------------------------------

        "conversation_history": conversation_history,

        # --------------------------------------------------------
        # Case identity
        # --------------------------------------------------------

        "case_id": state.get(
            "case_id",
            "",
        ),

        "session_id": state.get(
            "session_id",
            "",
        ),

        # --------------------------------------------------------
        # Current routing
        # --------------------------------------------------------

        "domain": state.get(
            "domain",
            "",
        ),

        "previous_domain": state.get(
            "previous_domain",
            "",
        ),

        "issue_type": state.get(
            "issue_type",
            "",
        ),


        # --------------------------------------------------------
        # Known entities
        # --------------------------------------------------------

        "order_id": state.get(
            "order_id",
            "",
        ),

        "customer_id": state.get(
            "customer_id",
            "",
        ),

        "product_id": state.get(
            "product_id",
            "",
        ),

        # --------------------------------------------------------
        # Transaction
        # --------------------------------------------------------

        "transaction_amount": state.get(
            "transaction_amount",
        ),

        "transaction_currency": state.get(
            "transaction_currency",
        ),

        # --------------------------------------------------------
        # Case/workflow status
        # --------------------------------------------------------

        "status": state.get(
            "status",
            "",
        ),

        "case_completed": state.get(
            "case_completed",
            False,
        ),

        "partially_completed": state.get(
            "partially_completed",
            False,
        ),

        "pending_information": state.get(
            "pending_information",
            [],
        ),

        # --------------------------------------------------------
        # Resolution
        # --------------------------------------------------------

        "resolution_success": state.get(
            "resolution_success",
            False,
        ),

        "resolution_result": state.get(
            "resolution_result",
            {},
        ),

        # --------------------------------------------------------
        # Action
        # --------------------------------------------------------

        "action_result": state.get(
            "action_result",
            {},
        ),

        # --------------------------------------------------------
        # Authorization
        #
        # These are included only so the model can understand
        # customer-facing workflow state. The prompt explicitly
        # prevents exposing internal flags/thresholds.
        # --------------------------------------------------------

        "authorization_required": state.get(
            "requires_human",
            False,
        ),

        "authorization_status": state.get(
            "human_approval",
            "",
        ),

        "approval_reason": state.get(
            "approval_reason",
            "",
        ),

        # --------------------------------------------------------
        # Validation
        # --------------------------------------------------------

        "validation_success": state.get(
            "validation_success",
            False,
        ),

        "validation_result": state.get(
            "validation_result",
            {},
        ),

        # --------------------------------------------------------
        # Case progress
        # --------------------------------------------------------

        "required_dependencies": state.get(
            "required_dependencies",
            [],
        ),

        "completed_dependencies": state.get(
            "completed_dependencies",
            [],
        ),
    }


# ============================================================
# CONTENT EXTRACTION
# ============================================================

def _extract_response_text(
    content,
) -> str:
    """
    Extract text from Gemini's response.

    Gemini may return either:
    - a string
    - a list of content blocks
    """

    if isinstance(
        content,
        str,
    ):
        return content.strip()

    if isinstance(
        content,
        list,
    ):

        text_parts: list[str] = []

        for block in content:

            if isinstance(
                block,
                dict,
            ):

                if block.get("type") == "text":

                    text = block.get(
                        "text",
                        "",
                    )

                    if text:
                        text_parts.append(
                            str(text)
                        )

            elif isinstance(
                block,
                str,
            ):

                text_parts.append(block)

        return "\n".join(
            text_parts
        ).strip()

    return str(
        content
    ).strip()


# ============================================================
# CUSTOMER RESPONSE NODE
# ============================================================

def customer_response_node(
    state: CaseState,
) -> dict:
    """
    Generate the final customer-facing response.

    Gemini receives:
    - latest customer message
    - conversation history
    - verified customer-safe case state

    Gemini does NOT receive unrestricted internal implementation
    state.
    """

    safe_state = _safe_customer_state(
        state
    )

    prompt = (
        CUSTOMER_RESPONSE_PROMPT
        + "\n\n"
        + "=========================================================\n"
        + "VERIFIED CASE INFORMATION\n"
        + "=========================================================\n"
        + json.dumps(
            safe_state,
            indent=2,
            default=str,
        )
        + "\n\n"
        + "Write ONLY the final customer-facing response now."
    )

    message = _critical_customer_message(state)
    if not message:
        try:
            response = model.invoke(prompt)
            message = _extract_response_text(response.content)
        except Exception:
            message = ""

    if not message:
        message = _fallback_customer_message(state)

    case_history = list(state.get("case_conversation_history") or [])
    case_history.append({"role": "assistant", "content": message})
    return {
        "customer_response": message,
        "case_conversation_history": case_history,
        "status": _customer_status(state),
    }



def _critical_customer_message(state: CaseState) -> str:
    status = str(state.get("status") or "")
    action = str(state.get("action_type") or "").upper()
    order_id = str(state.get("order_id") or "").strip()
    amount = state.get("transaction_amount")
    currency = str(state.get("transaction_currency") or "").upper().strip()
    reason = str(state.get("approval_reason") or "").strip()

    if status == "WAITING_FOR_HUMAN_APPROVAL":
        if action == "CREATE_REFUND" and amount is not None:
            amount_text = f"{currency} {float(amount):,.2f}" if currency else f"{float(amount):,.2f}"
            target = f" for order {order_id}" if order_id else ""
            return (
                f"The refund of {amount_text}{target} requires additional approval "
                "before it can be processed. No refund has been created yet."
            )
        return "Your requested action requires additional approval before it can be completed."

    if status == "HUMAN_REJECTED":
        message = "The requested financial action was not approved, so it was not executed. No financial transaction was made."
        return f"{message} {reason}".strip() if reason else message

    return ""

# ============================================================
# FALLBACK CUSTOMER RESPONSE
# ============================================================

def _fallback_customer_message(
    state: CaseState,
) -> str:
    """
    Deterministic fallback used if the response model fails.

    The fallback deliberately avoids claiming that an action
    succeeded unless validation confirms it.
    """

    status = state.get(
        "status",
        "",
    )

    pending_information = state.get(
        "pending_information",
        [],
    )

    if pending_information:

        first_item = str(
            pending_information[0]
        ).strip()

        if first_item:
            return (
                "I need "
                f"{first_item} "
                "before I can continue."
            )

        return (
            "I need a little more information "
            "before I can continue."
        )

    if status == "WAITING_FOR_HUMAN_APPROVAL":

        return (
            "Your request requires human approval before "
            "the requested financial action can be executed."
        )

    if status == "HUMAN_REJECTED":
        reason = str(state.get("approval_reason", "")).strip()
        if reason:
            return (
                "The requested financial action was not approved, "
                "so it was not executed. Reason: " + reason
            )
        return (
            "The requested financial action was not approved, "
            "so it was not executed. No financial transaction was made."
        )

    if status == "HUMAN_ESCALATION":

        return (
            "I couldn't complete the request automatically. "
            "A support specialist will continue reviewing "
            "the case."
        )

    if status == "WAITING_FOR_INFORMATION":

        return (
            "I need a little more information before "
            "I can continue with your request."
        )

    if status in {
        "INVESTIGATION_FAILED",
        "FAILED",
    }:

        return (
            "I couldn't verify everything needed to "
            "complete your request. A support specialist "
            "will continue reviewing the case."
        )

    if state.get(
        "partially_completed",
        False,
    ):

        return (
            "I've completed the available step, but "
            "your request still requires further processing."
        )

    if state.get(
        "case_completed",
        False,
    ):

        return (
            "Your request has been completed."
        )

    return (
        "I've checked your request, but I need "
        "a little more information before I can continue."
    )


# ============================================================
# CUSTOMER-FACING STATUS
# ============================================================

def _customer_status(
    state: CaseState,
) -> str:
    """
    Convert internal workflow state into a customer-facing
    status.

    IMPORTANT:

    Action success or strategy success does NOT automatically
    mean the complete case is resolved.

    Case completion requires the explicit case_completed state.
    """

    status = state.get(
        "status",
        "",
    )

    # --------------------------------------------------------
    # Human approval
    # --------------------------------------------------------

    if status == "WAITING_FOR_HUMAN_APPROVAL":

        return "CUSTOMER_AWAITING_HUMAN"

    # --------------------------------------------------------
    # Human escalation
    # --------------------------------------------------------

    if status == "HUMAN_ESCALATION":

        return "CUSTOMER_ESCALATED"

    # --------------------------------------------------------
    # Missing information
    # --------------------------------------------------------

    if status in {
        "WAITING_FOR_INFORMATION",
        "AWAITING_TRANSACTION_INFORMATION",
    }:

        return "CUSTOMER_NEEDS_INFORMATION"

    # --------------------------------------------------------
    # Investigation failure
    # --------------------------------------------------------

    if status == "INVESTIGATION_FAILED":

        return "CUSTOMER_NEEDS_INFORMATION"

    # --------------------------------------------------------
    # Explicit complete case
    # --------------------------------------------------------

    if state.get(
        "case_completed",
        False,
    ):

        return "RESOLUTION_COMPLETED"

    # --------------------------------------------------------
    # Partial completion
    # --------------------------------------------------------

    if state.get(
        "partially_completed",
        False,
    ):

        return "RESOLUTION_IN_PROGRESS"

    # --------------------------------------------------------
    # Validation failure
    # --------------------------------------------------------

    if status == "FAILED":

        return "CUSTOMER_NEEDS_INFORMATION"

    # --------------------------------------------------------
    # Otherwise continue
    # --------------------------------------------------------

    return "CUSTOMER_RESPONSE_READY"