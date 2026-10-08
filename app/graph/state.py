from __future__ import annotations

import operator

from typing import Annotated, Literal
from typing_extensions import TypedDict


Domain = Literal[
    "ORDER",
    "PAYMENT",
    "DELIVERY",
    "REFUND",
    "RETURN",
    "CANCELLATION",
    "PRODUCT_QUERY",
]

Authorization = Literal[
    "AI_ALLOWED",
    "HUMAN_REQUIRED",
    "NOT_REQUIRED",
    "PENDING",
]

CaseStatus = Literal[
    "NEW_REQUEST",
    "UNDERSTANDING",
    "ROUTING",
    "INVESTIGATING",
    "PLANNING",
    "WAITING_FOR_INFORMATION",
    "WAITING_FOR_HUMAN_APPROVAL",
    "HUMAN_APPROVED",
    "HUMAN_REJECTED",
    "EXECUTING",
    "VALIDATING",
    "DOMAIN_COMPLETED",
    "REROUTING",
    "IN_PROGRESS",
    "COMPLETED",
    "PARTIALLY_COMPLETED",
    "FAILED",
]


class ConversationMessage(TypedDict, total=False):
    role: str
    content: str


class ResolutionAttempt(TypedDict, total=False):
    strategy: str
    domain: str
    action: str
    success: bool
    error_code: str
    reason: str
    result: dict


class DomainTransition(TypedDict, total=False):
    from_domain: str | None
    to_domain: str
    reason: str
    trigger: str
    validated: bool


class ActionRecord(TypedDict, total=False):
    action_type: str
    action_key: str
    domain: str
    order_id: str | None
    refund_id: str | None
    amount: float | None
    success: bool
    message: str
    error_code: str


class CaseState(TypedDict, total=False):
    # Conversation
    session_id: str
    customer_message: str
    conversation_history: Annotated[list[ConversationMessage], operator.add]
    case_conversation_history: list[ConversationMessage]
    pending_information: list[str]
    is_acknowledgement: bool
    topic_changed: bool

    # Case/entity identity
    case_id: str
    customer_id: str | None
    order_id: str | None
    product_id: str | None
    refund_id: str | None

    # Routing
    domain: Domain | str
    previous_domain: str | None
    next_domain: str | None
    issue_type: str
    domain_confidence: float
    routing_reason: str
    reroute_count: int
    visited_domains: list[str]
    domain_history: list[DomainTransition]

    # Investigation/evidence
    investigation: str
    evidence: dict
    transaction_amount: float | None
    transaction_currency: str | None
    transaction_amount_status: str

    # Planning/dependencies
    next_step: str
    required_dependencies: list[str]
    completed_dependencies: list[str]

    # Authorization
    authorization: Authorization
    authorization_reason: str
    human_approval_threshold: float | None
    approval_reason: str
    requires_human: bool
    pending_authorization_action: str | None
    human_approval: str
    action_authorized: bool

    # Action
    action_required: bool
    action_ready: bool
    action_type: str
    action_reason: str
    action_key: str
    action_result: dict
    action_history: list[ActionRecord]
    executed_action_keys: list[str]
    action_already_executed: bool

    # Resolution
    current_strategy: str
    attempted_strategies: list[str]
    resolution_attempts: list[ResolutionAttempt]
    resolution_success: bool
    resolution_result: dict
    resolution_failure_reason: str

    # Validation / completion
    validation_success: bool
    validation_result: dict
    validation_failure_reason: str
    case_completed: bool
    partially_completed: bool

    # Recovery/errors
    recovery_attempts: int
    last_error_code: str
    last_error_message: str
    replan_required: bool

    # Customer response
    customer_response: str
    status: CaseStatus | str
