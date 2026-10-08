from __future__ import annotations

import re
from typing import Any

from app.agents.agent import casepilot_agent
from app.graph.state import CaseState
from app.graph.policy import authorization_decision, currency_from_country, normalize_currency
from app.tools.refund_lookup import get_refund_details_by_id


# ============================================================
# CONSTANTS
# ============================================================



SUPPORTED_DOMAINS = {
    "ORDER",
    "PAYMENT",
    "DELIVERY",
    "REFUND",
    "RETURN",
    "CANCELLATION",
    "PRODUCT_QUERY",
}


FINANCIAL_DOMAINS = {
    "PAYMENT",
    "REFUND",
}


# ============================================================
# RESPONSE TEXT EXTRACTION
# ============================================================

def _extract_text(
    content: Any,
) -> str:
    """
    Convert an LLM response into plain text.

    Gemini/LangChain responses can sometimes contain plain
    strings or structured content blocks.
    """

    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):

        text_parts: list[str] = []

        for block in content:

            if isinstance(
                block,
                dict,
            ):

                if block.get(
                    "type"
                ) == "text":

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

                text_parts.append(
                    block
                )

        return "\n".join(
            text_parts
        )

    return str(content)


# ============================================================
# EXACT IDENTIFIER EXTRACTION
# ============================================================

def _extract_order_id(
    text: str,
) -> str | None:
    """
    Extract an exact order identifier from customer-provided
    text.

    Important:
        ORD000004 remains ORD000004.

    We never pad or normalize the identifier.
    """

    if not text:
        return None

    match = re.search(
        r"\bORD[A-Z0-9]*[0-9][A-Z0-9]*\b",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(0).upper()


def _extract_customer_id(
    text: str,
) -> str | None:
    """
    Extract an exact customer identifier.
    """

    if not text:
        return None

    match = re.search(
        r"\bCUST[A-Z0-9]*[0-9][A-Z0-9]*\b",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(0).upper()


def _extract_product_id(
    text: str,
) -> str | None:
    """
    Extract an exact product identifier.
    """

    if not text:
        return None

    match = re.search(
        r"\b(?:PROD|P)[A-Z0-9]*[0-9][A-Z0-9]*\b",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(0).upper()


def _extract_refund_id(
    text: str,
) -> str | None:
    """Extract an exact refund identifier such as REF00000018."""

    if not text:
        return None

    match = re.search(
        r"\bREF[A-Z0-9]*[0-9][A-Z0-9]*\b",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(0).upper()


# ============================================================
# TRANSACTION AMOUNT EXTRACTION
# ============================================================

def _extract_transaction_amount(
    text: str,
) -> float | None:
    """
    Extract the transaction amount explicitly reported by the
    investigation agent.

    Expected:

        TRANSACTION_AMOUNT: 1999.00

    or:

        TRANSACTION_AMOUNT: UNKNOWN
    """

    if not text:
        return None

    match = re.search(
        r"TRANSACTION_AMOUNT\s*:\s*"
        r"(?:₹|Rs\.?|INR)?\s*"
        r"([0-9]+(?:\.[0-9]+)?)",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    try:

        amount = float(
            match.group(1)
        )

        if amount < 0:
            return None

        return amount

    except (
        TypeError,
        ValueError,
    ):

        return None


# ============================================================
# TRANSACTION AMOUNT STATUS
# ============================================================

def _contains_unknown_transaction_amount(
    text: str,
) -> bool:
    """
    Detect the explicit UNKNOWN marker emitted by the
    investigation agent.
    """

    return bool(
        re.search(
            r"TRANSACTION_AMOUNT\s*:\s*UNKNOWN",
            text,
            re.IGNORECASE,
        )
    )


# ============================================================
# ACKNOWLEDGEMENT DETECTION
# ============================================================

def _is_acknowledgement(
    text: str,
) -> bool:
    """
    Detect simple conversational acknowledgements.

    These should not cause a completely new investigation.
    """

    normalized = (
        text
        .strip()
        .lower()
    )

    acknowledgement_values = {
        "ok",
        "okay",
        "k",
        "thanks",
        "thank you",
        "got it",
        "alright",
        "sure",
        "fine",
        "understood",
        "yes",
        "yep",
        "yeah",
    }

    return normalized in acknowledgement_values


# ============================================================
# DOMAIN EXTRACTION FROM STATE
# ============================================================

def _get_domain(
    state: CaseState,
) -> str | None:
    """
    Return the currently routed domain.
    """

    domain = state.get(
        "domain"
    )

    if not domain:
        return None

    domain = str(
        domain
    ).upper()

    if domain not in SUPPORTED_DOMAINS:
        return None

    return domain


# ============================================================
# VERIFIED ENTITY RESOLUTION
# ============================================================

def _resolve_entity_ids(
    state: CaseState,
    customer_message: str,
) -> dict:
    """
    Resolve identifiers from the current customer turn first.

    Rules:
        1. An explicit current-turn identifier always wins.
        2. A malformed-but-recognisable identifier is still preserved exactly.
        3. A new entity type clears stale incompatible entity context.
        4. If the customer gives no new identifier, verified state is reused.
        5. Never extract operational identifiers from the LLM response.
    """

    updates: dict = {}

    message_order_id = _extract_order_id(customer_message)
    message_customer_id = _extract_customer_id(customer_message)
    message_product_id = _extract_product_id(customer_message)
    message_refund_id = _extract_refund_id(customer_message)

    existing_order_id = state.get("order_id")
    existing_customer_id = state.get("customer_id")
    existing_product_id = state.get("product_id")
    existing_refund_id = state.get("refund_id")

    # A new order reference replaces the previous order reference.
    if message_order_id:
        updates["order_id"] = message_order_id
    elif message_product_id or message_refund_id:
        # The customer switched to another entity type in this turn.
        updates["order_id"] = None
    elif existing_order_id:
        updates["order_id"] = existing_order_id

    if message_product_id:
        updates["product_id"] = message_product_id
    elif message_order_id:
        # An order reference may later resolve its product from RDS.
        updates["product_id"] = None
    elif existing_product_id:
        updates["product_id"] = existing_product_id

    if message_refund_id:
        updates["refund_id"] = message_refund_id
    elif message_order_id:
        updates["refund_id"] = None
    elif existing_refund_id:
        updates["refund_id"] = existing_refund_id

    if message_customer_id:
        updates["customer_id"] = message_customer_id
    elif existing_customer_id:
        updates["customer_id"] = existing_customer_id

    return updates


# ============================================================
# CONVERSATION CONTEXT
# ============================================================

def _build_agent_messages(
    history: list,
) -> list[dict[str, str]]:
    """
    Convert stored CasePilot conversation history into the
    message structure expected by the investigation agent.
    """

    messages: list[
        dict[str, str]
    ] = []

    for message in history:

        if not isinstance(
            message,
            dict,
        ):
            continue

        role = message.get(
            "role"
        )

        content = message.get(
            "content"
        )

        if not role:
            continue

        if content is None:
            continue

        content = str(
            content
        ).strip()

        if not content:
            continue

        if role not in {
            "user",
            "assistant",
            "system",
        }:
            continue

        messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    return messages


# ============================================================
# CASE INVESTIGATION
# ============================================================

def investigate_case(
    state: CaseState,
) -> CaseState:
    """
    Investigate the customer's current issue.

    Responsibilities:

        - understand the current turn
        - preserve conversation context
        - use read-only tools through the investigation agent
        - gather operational/policy evidence
        - preserve exact customer-provided IDs
        - extract a transaction amount when explicitly reported
        - never perform write actions

    This node does NOT decide whether a transaction is allowed.
    Authorization is handled separately.
    """

    customer_message = (
        state.get(
            "customer_message",
            "",
        )
        .strip()
    )

    # ========================================================
    # VALIDATE MESSAGE
    # ========================================================

    if not customer_message:

        return {
            "status": "INVESTIGATION_FAILED",
            "investigation": (
                "No customer message was provided."
            ),
            "last_error_code": (
                "EMPTY_CUSTOMER_MESSAGE"
            ),
            "last_error_message": (
                "The customer message was empty."
            ),
        }

    # ========================================================
    # ACKNOWLEDGEMENT
    # ========================================================

    acknowledgement = (
        _is_acknowledgement(
            customer_message
        )
    )

    # Simple acknowledgements should not trigger a fresh
    # database investigation when an existing case already
    # contains meaningful context.

    if acknowledgement and state.get(
        "investigation"
    ):

        return {
            "is_acknowledgement": True,
            "status": "IN_PROGRESS",
            "investigation": state.get(
                "investigation",
                "",
            ),
        }

    # ========================================================
    # EXACT ENTITY RESOLUTION
    # ========================================================

    entity_updates = _resolve_entity_ids(
        state=state,
        customer_message=customer_message,
    )

    # An explicit RefundID is an authoritative operational identifier.
    # Resolve its order/customer/amount directly from RDS before
    # the investigation result can influence transaction state.
    refund_id = entity_updates.get("refund_id")
    if refund_id:
        refund_lookup = get_refund_details_by_id.invoke({"refund_id": refund_id})
        if refund_lookup.get("success"):
            refund = refund_lookup.get("refund", {}) or {}
            entity_updates["refund_id"] = refund.get("refund_id", refund_id)
            entity_updates["order_id"] = refund.get("order_id")
            entity_updates["customer_id"] = refund.get("customer_id")
            try:
                entity_updates["transaction_amount"] = float(refund.get("refund_amount"))
            except (TypeError, ValueError):
                pass
        else:
            entity_updates["last_error_code"] = refund_lookup.get("error_code", "REFUND_NOT_FOUND")
            entity_updates["last_error_message"] = refund_lookup.get("message", "The refund could not be verified.")

    # ========================================================
    # BUILD CONVERSATION
    # ========================================================

    history = state.get(
        "case_conversation_history",
        state.get("conversation_history", []),
    )

    agent_messages = _build_agent_messages(
        history
    )

    # ========================================================
    # ENSURE CURRENT MESSAGE EXISTS
    # ========================================================

    if not agent_messages or (
        agent_messages[-1].get(
            "role"
        ) != "user"
        or agent_messages[-1].get(
            "content"
        ) != customer_message
    ):

        agent_messages.append(
            {
                "role": "user",
                "content": customer_message,
            }
        )

    # ========================================================
    # INVESTIGATION AGENT
    # ========================================================

    try:

        result = casepilot_agent.invoke(
            {
                "messages": agent_messages,
            }
        )

    except Exception as exc:

        # pyrefly: ignore [bad-unpacking]
        return {
            **entity_updates,
            "status": "INVESTIGATION_FAILED",
            "investigation": (
                "The investigation agent failed."
            ),
            "last_error_code": (
                "INVESTIGATION_AGENT_ERROR"
            ),
            "last_error_message": str(
                exc
            ),
            "resolution_failure_reason": (
                str(exc)
            ),
        }

    # ========================================================
    # EXTRACT AGENT MESSAGES
    # ========================================================

    messages = result.get(
        "messages",
        [],
    )

    if not messages:

        # pyrefly: ignore [bad-unpacking]
        return {
            **entity_updates,
            "status": "INVESTIGATION_FAILED",
            "investigation": (
                "The investigation agent returned "
                "no messages."
            ),
            "last_error_code": (
                "EMPTY_AGENT_RESPONSE"
            ),
            "last_error_message": (
                "No messages were returned by "
                "the investigation agent."
            ),
        }

    # ========================================================
    # FIND FINAL TEXT RESPONSE
    # ========================================================

    investigation_text = ""

    for message in reversed(
        messages
    ):

        content = getattr(
            message,
            "content",
            None,
        )

        text = _extract_text(
            content
        ).strip()

        if text:

            investigation_text = text

            break

    if not investigation_text:

        # pyrefly: ignore [bad-unpacking]
        return {
            **entity_updates,
            "status": "INVESTIGATION_FAILED",
            "investigation": (
                "The investigation agent returned "
                "an empty response."
            ),
            "last_error_code": (
                "EMPTY_INVESTIGATION_TEXT"
            ),
            "last_error_message": (
                "The investigation response contained "
                "no usable text."
            ),
        }

    # ========================================================
    # TRANSACTION AMOUNT
    # ========================================================

    transaction_amount = (
        _extract_transaction_amount(
            investigation_text
        )
    )

    # When an order is known, the RDS order amount is authoritative.
    # A customer/LLM-stated amount must never override it.
    if entity_updates.get("order_id") and not entity_updates.get("refund_id"):
        try:
            from app.tools.read_tools import get_order_details
            verified_order = get_order_details.invoke({"order_id": entity_updates["order_id"]})
            if verified_order.get("success"):
                verified_amount = verified_order.get("order", {}).get("total_amount")
                if verified_amount is None:
                    verified_amount = verified_order.get("order", {}).get("TotalAmount")
                if verified_amount is not None:
                    transaction_amount = float(verified_amount)
        except Exception:
            pass

    # ========================================================
    # CURRENT DOMAIN
    # ========================================================

    domain = _get_domain(
        state
    )

    # ========================================================
    # BUILD EVIDENCE
    # ========================================================

    evidence = dict(
        state.get(
            "evidence",
            {},
        )
        or {}
    )

    evidence[
        "latest_investigation"
    ] = investigation_text

    if transaction_amount is not None:

        evidence[
            "transaction_amount"
        ] = transaction_amount

    if _contains_unknown_transaction_amount(
        investigation_text
    ):

        evidence[
            "transaction_amount_status"
        ] = "UNKNOWN"

    # ========================================================
    # BUILD STATE UPDATE
    # ========================================================

    # pyrefly: ignore [bad-unpacking]
    updates: CaseState = {

        **entity_updates,

        "investigation": (
            investigation_text
        ),

        "evidence": evidence,

        "is_acknowledgement": False,

        "status": (
            "INVESTIGATION_COMPLETED"
        ),
    }

    # --------------------------------------------------------
    # Preserve transaction amount only when explicitly known.
    #
    # Do NOT erase a previously verified amount merely because
    # the latest turn is informational.
    # --------------------------------------------------------

    if transaction_amount is not None:

        updates[
            "transaction_amount"
        ] = transaction_amount

    # ========================================================
    # DOMAIN TRACKING
    # ========================================================

    if domain:

        visited_domains = list(
            state.get(
                "visited_domains",
                [],
            )
            or []
        )

        if domain not in visited_domains:

            visited_domains.append(
                domain
            )

        updates[
            "visited_domains"
        ] = visited_domains

    # ========================================================
    # IMPORTANT:
    #
    # Do NOT append the investigation agent's internal
    # investigation summary to customer conversation history.
    #
    # The customer-facing response node will generate the
    # actual assistant message.
    # ========================================================

    return updates


# ============================================================
# AUTHORIZATION GATE
# ============================================================

def authorization_gate(state: CaseState) -> dict[str, Any]:
    """Apply the currency-aware CasePilot financial authorization policy."""
    action_type = str(state.get("action_type", "")).upper().strip()

    if action_type != "CREATE_REFUND":
        return {
            "authorization": "NOT_REQUIRED",
            "authorization_reason": "This action is not a financial transaction.",
            "requires_human": False,
            "action_authorized": True,
            "pending_authorization_action": None,
            "human_approval_threshold": None,
            "status": "AI_CAN_PROCEED",
        }

    amount = state.get("transaction_amount")
    if amount is None:
        return {
            "authorization": "PENDING",
            "authorization_reason": "A verified transaction amount is required before the financial action can proceed.",
            "requires_human": False,
            "action_authorized": False,
            "pending_authorization_action": action_type,
            "human_approval_threshold": None,
            "status": "AWAITING_TRANSACTION_INFORMATION",
            "pending_information": ["transaction amount"],
        }

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return {
            "authorization": "PENDING",
            "authorization_reason": "The transaction amount could not be determined.",
            "requires_human": False,
            "action_authorized": False,
            "pending_authorization_action": action_type,
            "human_approval_threshold": None,
            "status": "AWAITING_TRANSACTION_INFORMATION",
            "pending_information": ["transaction amount"],
            "last_error_code": "INVALID_TRANSACTION_AMOUNT",
            "last_error_message": "The transaction amount could not be determined.",
        }

    if amount < 0:
        return {
            "authorization": "PENDING",
            "authorization_reason": "A transaction amount cannot be negative.",
            "requires_human": False,
            "action_authorized": False,
            "pending_authorization_action": action_type,
            "human_approval_threshold": None,
            "status": "FAILED",
            "last_error_code": "INVALID_TRANSACTION_AMOUNT",
            "last_error_message": "A transaction amount cannot be negative.",
        }

    currency = normalize_currency(state.get("transaction_currency"))
    if not currency:
        evidence = state.get("evidence") or {}
        if isinstance(evidence, dict):
            order = evidence.get("order")
            if isinstance(order, dict):
                currency = currency_from_country(order.get("country"))

    try:
        decision = authorization_decision(amount, currency)
    except Exception as exc:
        return {
            "authorization": "HUMAN_REQUIRED",
            "authorization_reason": f"CasePilot policy could not be read safely: {exc}",
            "requires_human": True,
            "action_authorized": False,
            "pending_authorization_action": action_type,
            "human_approval_threshold": None,
            "status": "HUMAN_ESCALATION",
            "last_error_code": "CASEPILOT_POLICY_UNAVAILABLE",
            "last_error_message": str(exc),
        }

    return {
        "authorization": decision["authorization"],
        "requires_human": decision["requires_human"],
        "action_authorized": not decision["requires_human"],
        "transaction_currency": currency,
        "human_approval_threshold": decision.get("threshold"),
        "authorization_reason": decision.get("reason", ""),
        "status": "WAITING_FOR_HUMAN_APPROVAL" if decision["requires_human"] else "AI_CAN_PROCEED",
        "pending_authorization_action": action_type if decision["requires_human"] else None,
    }

