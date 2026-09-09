from __future__ import annotations

from typing import Literal
from typing_extensions import TypedDict


class CaseState(TypedDict, total=False):
    # Customer input
    customer_message: str

    # Case information
    case_id: str
    order_id: str
    domain: str
    issue_type: str

    # Investigation
    investigation: str
    transaction_amount: float

    # Authorization
    authorization: Literal["AI_ALLOWED", "HUMAN_REQUIRED"]
    requires_human: bool

    # Current status
    status: str