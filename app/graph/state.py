from __future__ import annotations

import operator

from typing import Annotated, Literal
from typing_extensions import TypedDict


class CaseState(TypedDict, total=False):
    # -------------------------------------------------
    # Conversation
    # -------------------------------------------------

    session_id: str

    customer_message: str

    conversation_history: Annotated[
        list[dict[str, str]],
        operator.add,
    ]

    # -------------------------------------------------
    # Customer / case information
    # -------------------------------------------------

    customer_id: str
    order_id: str

    case_id: str
    domain: str
    issue_type: str

    # -------------------------------------------------
    # Investigation
    # -------------------------------------------------

    investigation: str
    transaction_amount: float

    # -------------------------------------------------
    # Authorization
    # -------------------------------------------------

    authorization: Literal[
        "AI_ALLOWED",
        "HUMAN_REQUIRED",
    ]

    requires_human: bool

    # -------------------------------------------------
    # Status
    # -------------------------------------------------

    status: str