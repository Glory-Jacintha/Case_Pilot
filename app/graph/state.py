from __future__ import annotations

import operator

from typing import Annotated, Literal
from typing_extensions import TypedDict


class ResolutionAttempt(TypedDict, total=False):
    strategy: str
    action: str
    success: bool
    error_code: str
    reason: str
    result: dict


class CaseState(TypedDict, total=False):

    # =================================================
    # Conversation
    # =================================================

    session_id: str

    customer_message: str

    conversation_history: Annotated[
        list[dict[str, str]],
        operator.add,
    ]

    # =================================================
    # Case identification
    # =================================================

    case_id: str

    customer_id: str

    order_id: str

    domain: str

    issue_type: str

    # =================================================
    # Investigation
    # =================================================

    investigation: str

    transaction_amount: float

    # =================================================
    # Authorization
    # =================================================

    authorization: Literal[
        "AI_ALLOWED",
        "HUMAN_REQUIRED",
    ]

    requires_human: bool

    # =================================================
    # Resolution
    # =================================================

    current_strategy: str

    attempted_strategies: list[str]

    resolution_attempts: list[
        ResolutionAttempt
    ]

    resolution_success: bool

    resolution_result: dict

    resolution_failure_reason: str

    # =================================================
    # Customer response
    # =================================================

    customer_response: str

    # =================================================
    # Status
    # =================================================

    status: str