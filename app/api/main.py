from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from langgraph.types import Command

from app.graph.graph import casepilot_graph


app = FastAPI(
    title="CasePilot API",
    description="AI-powered customer support resolution API",
    version="1.1.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Request / Response models
# ============================================================

class ChatRequest(BaseModel):
    session_id: str = Field(
        ...,
        min_length=1,
        description="Unique customer conversation/session ID",
    )

    customer_message: str = Field(
        ...,
        min_length=1,
        description="Message sent by the customer",
    )


class ChatResponse(BaseModel):
    message: str
    transaction_amount: float | None = None
    transaction_currency: str | None = None
    authorization: str | None = None
    requires_human: bool = False
    status: str


class HumanDecisionRequest(BaseModel):
    reason: str = Field(
        default="",
        description="Optional reason recorded with the human decision",
    )


# ============================================================
# In-process pending-review registry
# ============================================================
#
# The LangGraph MemorySaver is currently an in-process
# checkpointer. This registry therefore also lives in process.
#
# This is suitable for local development/demo integration.
# Production durability will require a persistent checkpointer
# and persistent case/review records.
# ============================================================

PENDING_REVIEW_THREADS: dict[str, str] = {}
HISTORY_CASES: dict[str, dict[str, Any]] = {}


# ============================================================
# Helpers
# ============================================================

def _config(thread_id: str) -> dict[str, Any]:
    return {
        "configurable": {
            "thread_id": thread_id,
        }
    }


def _json_safe(value: Any) -> Any:
    """Convert LangGraph/Python values into JSON-safe values."""

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _json_safe(item)
            for item in value
        ]

    if hasattr(value, "value"):
        try:
            return _json_safe(value.value)
        except Exception:
            pass

    return str(value)


def _get_snapshot(thread_id: str):
    return casepilot_graph.get_state(
        _config(thread_id)
    )


def _get_interrupt_payload(snapshot) -> dict[str, Any] | None:
    interrupts = getattr(
        snapshot,
        "interrupts",
        (),
    )

    if not interrupts:
        return None

    interrupt_item = interrupts[0]

    value = getattr(
        interrupt_item,
        "value",
        None,
    )

    if isinstance(value, dict):
        return _json_safe(value)

    return {
        "value": _json_safe(value)
    }


def _is_waiting_for_human(snapshot) -> bool:
    return bool(
        getattr(snapshot, "interrupts", ())
    )


def _build_review_case(
    thread_id: str,
    snapshot,
) -> dict[str, Any]:

    state = dict(
        getattr(snapshot, "values", {})
        or {}
    )

    interrupt_payload = _get_interrupt_payload(
        snapshot
    )

    case_id = str(
        state.get("case_id")
        or thread_id
    )

    workflow: list[str] = []
    history = state.get("domain_history") or []
    if isinstance(history, list):
        for transition in history:
            if not isinstance(transition, dict):
                continue
            from_domain = transition.get("from_domain") or transition.get("from")
            to_domain = transition.get("to_domain") or transition.get("to")
            if from_domain and str(from_domain) not in workflow:
                workflow.append(str(from_domain))
            if to_domain and str(to_domain) not in workflow:
                workflow.append(str(to_domain))

    current_domain = state.get("domain")
    if current_domain and str(current_domain) not in workflow:
        workflow.append(str(current_domain))

    return {
        "case_id": case_id,
        "session_id": thread_id,
        "status": state.get("status", "UNKNOWN"),
        "customer_id": state.get("customer_id"),
        "order_id": state.get("order_id"),
        "refund_id": state.get("refund_id"),
        "domain": state.get("domain"),
        "issue_type": state.get("issue_type"),
        "customer_message": state.get(
            "customer_message",
            "",
        ),
        "transaction_amount": (
            interrupt_payload.get("transaction_amount")
            if interrupt_payload else state.get("transaction_amount")
        ),
        "transaction_currency": (
            interrupt_payload.get("transaction_currency")
            if interrupt_payload else state.get("transaction_currency")
        ),
        "human_approval_threshold": (
            interrupt_payload.get("human_approval_threshold")
            if interrupt_payload else state.get("human_approval_threshold")
        ),
        "approval_reason": state.get(
            "approval_reason"
        ),
        "authorization": state.get(
            "authorization"
        ),
        "requires_human": state.get(
            "requires_human",
            True,
        ),
        "action_type": state.get(
            "action_type"
        ),
        "action_reason": state.get(
            "action_reason"
        ),
        "investigation": state.get(
            "investigation"
        ),
        "evidence": _json_safe(
            state.get(
                "evidence",
                {},
            )
        ),
        "resolution_result": _json_safe(
            state.get(
                "resolution_result",
                {},
            )
        ),
        "attempted_strategies": _json_safe(
            state.get(
                "attempted_strategies",
                [],
            )
        ),
        "resolution_attempts": _json_safe(
            state.get(
                "resolution_attempts",
                [],
            )
        ),
        "required_dependencies": _json_safe(
            state.get(
                "required_dependencies",
                [],
            )
        ),
        "completed_dependencies": _json_safe(
            state.get(
                "completed_dependencies",
                [],
            )
        ),
        "workflow": workflow,
        "interrupt": interrupt_payload,
    }


def _refresh_pending_registry() -> None:
    """
    Remove registry entries that are no longer interrupted.

    The graph itself remains the source of truth.
    """

    stale: list[str] = []

    for case_id, thread_id in list(
        PENDING_REVIEW_THREADS.items()
    ):
        try:
            snapshot = _get_snapshot(
                thread_id
            )

            if not _is_waiting_for_human(
                snapshot
            ):
                stale.append(case_id)

        except Exception:
            stale.append(case_id)

    for case_id in stale:
        PENDING_REVIEW_THREADS.pop(
            case_id,
            None,
        )


def _register_pending_review(
    thread_id: str,
    result: dict[str, Any],
) -> None:

    if "__interrupt__" not in result:
        return

    try:
        snapshot = _get_snapshot(
            thread_id
        )

        state = dict(
            getattr(snapshot, "values", {})
            or {}
        )

        case_id = str(
            state.get("case_id")
            or thread_id
        )

    except Exception:
        case_id = thread_id

    PENDING_REVIEW_THREADS[
        case_id
    ] = thread_id


def _save_case_history(thread_id: str) -> None:
    try:
        snapshot = _get_snapshot(thread_id)
        record = _build_review_case(thread_id, snapshot)
        case_id = str(record.get("case_id") or thread_id)
        HISTORY_CASES[case_id] = record
    except Exception:
        # History must never break the customer or human-review flow.
        return


# ============================================================
# Health
# ============================================================

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "casepilot-api",
        "langgraph": "connected",
    }


# ============================================================
# Customer chat
# ============================================================

@app.post(
    "/api/chat",
    response_model=ChatResponse,
)
def chat(request: ChatRequest):

    config = _config(
        request.session_id
    )

    result = casepilot_graph.invoke(
        {
            "session_id": request.session_id,
            "customer_message": request.customer_message,
            "conversation_history": [
                {
                    "role": "user",
                    "content": request.customer_message,
                }
            ],
        },
        config=config,
    )

    _register_pending_review(
        request.session_id,
        result,
    )
    _save_case_history(request.session_id)

    # A LangGraph interrupt means the case is paused.
    if "__interrupt__" in result:
        snapshot = _get_snapshot(
            request.session_id
        )

        state = dict(
            getattr(snapshot, "values", {})
            or {}
        )

        return ChatResponse(
            message=result.get(
                "customer_response",
                "Your request requires additional approval before it can be completed.",
            ),
            transaction_amount=state.get("transaction_amount"),
            transaction_currency=state.get("transaction_currency"),
            authorization=state.get("authorization"),
            requires_human=True,
            status="WAITING_FOR_HUMAN_APPROVAL",
        )

    return ChatResponse(
        message=result.get(
            "customer_response",
            "I'm checking your request.",
        ),
        transaction_amount=result.get(
            "transaction_amount"
        ),
        transaction_currency=result.get(
            "transaction_currency"
        ),
        authorization=result.get(
            "authorization"
        ),
        requires_human=result.get(
            "requires_human",
            False,
        ),
        status=result.get(
            "status",
            "UNKNOWN",
        ),
    )


# ============================================================
# Human Review - pending queue
# ============================================================

@app.get(
    "/api/human-review/pending"
)
def get_pending_reviews():

    _refresh_pending_registry()

    reviews: list[dict[str, Any]] = []

    for case_id, thread_id in list(
        PENDING_REVIEW_THREADS.items()
    ):
        try:
            snapshot = _get_snapshot(
                thread_id
            )

            if not _is_waiting_for_human(
                snapshot
            ):
                continue

            reviews.append(
                _build_review_case(
                    thread_id,
                    snapshot,
                )
            )

        except Exception as exc:
            # Keep the API alive if one stale thread
            # cannot be inspected.
            reviews.append(
                {
                    "case_id": case_id,
                    "session_id": thread_id,
                    "status": "REVIEW_STATE_ERROR",
                    "error": str(exc),
                }
            )

    return {
        "count": len(reviews),
        "cases": reviews,
    }


@app.get("/api/history")
def get_case_history():
    records = sorted(
        HISTORY_CASES.values(),
        key=lambda item: str(item.get("case_id", "")),
        reverse=True,
    )
    return {"count": len(records), "cases": records}


# ============================================================
# Human Review - inspect one case
# ============================================================

@app.get(
    "/api/human-review/{case_id}"
)
def get_human_review(
    case_id: str,
):

    _refresh_pending_registry()

    thread_id = PENDING_REVIEW_THREADS.get(
        case_id
    )

    if thread_id is None:
        # Also allow the session/thread ID itself.
        thread_id = case_id

    try:
        snapshot = _get_snapshot(
            thread_id
        )
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Case '{case_id}' was not found: "
                f"{exc}"
            ),
        ) from exc

    if not _is_waiting_for_human(
        snapshot
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This case is not currently waiting "
                "for human approval."
            ),
        )

    return _build_review_case(
        thread_id,
        snapshot,
    )


# ============================================================
# Human Review - approve
# ============================================================

@app.post(
    "/api/human-review/{case_id}/approve"
)
def approve_human_review(
    case_id: str,
    request: HumanDecisionRequest,
):

    _refresh_pending_registry()

    thread_id = PENDING_REVIEW_THREADS.get(
        case_id
    ) or case_id

    try:
        snapshot = _get_snapshot(
            thread_id
        )
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Case '{case_id}' was not found: "
                f"{exc}"
            ),
        ) from exc

    if not _is_waiting_for_human(
        snapshot
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This case is not waiting for "
                "human approval."
            ),
        )

    result = casepilot_graph.invoke(
        Command(
            resume={
                "approved": True,
                "reason": request.reason,
            }
        ),
        config=_config(thread_id),
    )

    PENDING_REVIEW_THREADS.pop(
        case_id,
        None,
    )
    _save_case_history(thread_id)

    if "__interrupt__" in result:
        _register_pending_review(
            thread_id,
            result,
        )

    return {
        "success": True,
        "decision": "APPROVED",
        "case_id": case_id,
        "status": result.get(
            "status",
            "PROCESSING",
        ),
        "message": result.get(
            "customer_response",
            "Human approval was recorded.",
        ),
        "transaction_amount": result.get(
            "transaction_amount"
        ),
        "transaction_currency": result.get(
            "transaction_currency"
        ),
        "authorization": result.get(
            "authorization"
        ),
        "requires_human": result.get(
            "requires_human",
            False,
        ),
        "action_result": _json_safe(
            result.get(
                "action_result",
                {},
            )
        ),
    }


# ============================================================
# Human Review - reject
# ============================================================

@app.post(
    "/api/human-review/{case_id}/reject"
)
def reject_human_review(
    case_id: str,
    request: HumanDecisionRequest,
):

    _refresh_pending_registry()

    thread_id = PENDING_REVIEW_THREADS.get(
        case_id
    ) or case_id

    try:
        snapshot = _get_snapshot(
            thread_id
        )
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Case '{case_id}' was not found: "
                f"{exc}"
            ),
        ) from exc

    if not _is_waiting_for_human(
        snapshot
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This case is not waiting for "
                "human approval."
            ),
        )

    result = casepilot_graph.invoke(
        Command(
            resume={
                "approved": False,
                "reason": request.reason,
            }
        ),
        config=_config(thread_id),
    )

    PENDING_REVIEW_THREADS.pop(
        case_id,
        None,
    )
    _save_case_history(thread_id)

    return {
        "success": True,
        "decision": "REJECTED",
        "case_id": case_id,
        "status": result.get(
            "status",
            "HUMAN_REJECTED",
        ),
        "message": result.get(
            "customer_response",
            "The requested action was rejected.",
        ),
        "transaction_amount": result.get(
            "transaction_amount"
        ),
        "transaction_currency": result.get(
            "transaction_currency"
        ),
        "authorization": result.get(
            "authorization"
        ),
        "requires_human": result.get(
            "requires_human",
            False,
        ),
        "action_result": _json_safe(
            result.get(
                "action_result",
                {},
            )
        ),
    }
