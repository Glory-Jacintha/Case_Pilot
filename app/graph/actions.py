from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from app.graph.policy import (
    authorization_decision,
    normalize_currency,
    resolve_transaction_currency,
)
from app.tools.action_tools import cancel_order, create_refund, process_return

SUPPORTED_ACTIONS = {
    "CREATE_REFUND",
    "CANCEL_ORDER",
    "PROCESS_RETURN",
}
FINANCIAL_ACTIONS = {"CREATE_REFUND"}


def _safe_float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _get_authorization(state: dict[str, Any]) -> dict[str, Any]:
    amount = _safe_float(state.get("transaction_amount"))
    currency = resolve_transaction_currency(state)
    if amount is None:
        return {
            "authorization": "PENDING",
            "requires_human": False,
            "threshold": None,
            "currency": currency,
            "reason": "A verified transaction amount is required before the financial action can proceed.",
        }
    try:
        result = authorization_decision(amount, currency)
    except Exception as exc:
        result = {
            "authorization": "HUMAN_REQUIRED",
            "requires_human": True,
            "threshold": None,
            "reason": f"CasePilot policy could not be read safely: {exc}",
        }
    result["currency"] = currency
    return result


def _make_key(
    action_type: str,
    order_id: str | None,
    customer_id: str | None,
    amount: float | None,
) -> str:
    amount_part = f"{amount:.2f}" if amount is not None else "UNKNOWN"
    return (
        f"{action_type.upper().strip()}:"
        f"{str(order_id or '').upper().strip()}:"
        f"{str(customer_id or '').upper().strip()}:"
        f"{amount_part}"
    )


def _history(
    state: dict[str, Any],
    record: dict[str, Any],
) -> list[dict[str, Any]]:
    return [*(state.get("action_history") or []), record]


def determine_action(state: dict[str, Any]) -> dict[str, Any]:
    """Select the write action after business validation.

    Authorization is intentionally handled by authorization_gate so there
    is one authoritative policy checkpoint before execution.
    """
    domain = str(state.get("domain") or "").upper().strip()
    order_id = state.get("order_id")
    customer_id = state.get("customer_id")
    amount = _safe_float(state.get("transaction_amount"))
    action_type = {
        "REFUND": "CREATE_REFUND",
        "RETURN": "PROCESS_RETURN",
        "CANCELLATION": "CANCEL_ORDER",
    }.get(domain, "")

    if not action_type:
        return {
            "action_required": False,
            "action_type": "",
            "action_reason": "",
            "action_key": "",
            "action_authorized": False,
            "requires_human": False,
            "authorization": "NOT_REQUIRED",
            "status": "NO_ACTION_REQUIRED",
        }

    if action_type == "CREATE_REFUND" and amount is None:
        return {
            "action_required": True,
            "action_type": action_type,
            "action_key": _make_key(action_type, order_id, customer_id, amount),
            "action_authorized": False,
            "requires_human": False,
            "authorization": "PENDING",
            "status": "WAITING_FOR_TRANSACTION_INFORMATION",
            "resolution_failure_reason": "A verified transaction amount is required before the financial action can proceed.",
            "pending_information": ["transaction amount"],
        }

    key = _make_key(action_type, order_id, customer_id, amount)
    executed = list(state.get("executed_action_keys") or [])
    if key in executed:
        return {
            "action_required": True,
            "action_type": action_type,
            "action_reason": "The requested action has already been executed.",
            "action_key": key,
            "action_authorized": True,
            "requires_human": False,
            "authorization": state.get("authorization", "AI_ALLOWED"),
            "action_already_executed": True,
            "status": "ACTION_ALREADY_EXECUTED",
        }

    reason = {
        "CREATE_REFUND": "The verified refund path requires a refund transaction.",
        "PROCESS_RETURN": "The verified return path requires the return operation to be processed.",
        "CANCEL_ORDER": "The verified cancellation path requires an order cancellation operation.",
    }[action_type]
    return {
        "action_required": True,
        "action_type": action_type,
        "action_reason": reason,
        "action_key": key,
        "action_authorized": False,
        "requires_human": False,
        "authorization": "PENDING" if action_type in FINANCIAL_ACTIONS else "NOT_REQUIRED",
        "pending_authorization_action": action_type if action_type in FINANCIAL_ACTIONS else None,
        "status": "ACTION_SELECTED",
    }


def request_human_approval(state: dict[str, Any]) -> dict[str, Any]:
    action_type = str(state.get("action_type") or "").upper().strip()
    amount = _safe_float(state.get("transaction_amount"))
    auth = _get_authorization(state)
    request = {
        "type": "TRANSACTION_APPROVAL",
        "action_type": action_type,
        "domain": state.get("domain", ""),
        "order_id": state.get("order_id", ""),
        "customer_id": state.get("customer_id", ""),
        "transaction_amount": amount,
        "transaction_currency": auth.get("currency"),
        "human_approval_threshold": auth.get("threshold"),
        "reason": state.get("action_reason", ""),
        "authorization_reason": auth.get("reason", ""),
        "evidence": state.get("evidence", {}),
        "investigation": state.get("investigation", ""),
        "resolution_result": state.get("resolution_result", {}),
    }
    decision = interrupt(request)
    if isinstance(decision, dict):
        approved = bool(decision.get("approved", False))
        reason = str(decision.get("reason") or "").strip()
    else:
        approved = bool(decision)
        reason = ""
    if approved:
        return {
            "action_authorized": True,
            "requires_human": False,
            "human_approval": "APPROVED",
            "approval_reason": reason,
            "authorization": "HUMAN_REQUIRED",
            "status": "HUMAN_APPROVED",
        }
    return {
        "action_authorized": False,
        "requires_human": False,
        "human_approval": "REJECTED",
        "approval_reason": reason,
        "authorization": "HUMAN_REQUIRED",
        "status": "HUMAN_REJECTED",
        "resolution_failure_reason": "Human approval was rejected; the requested financial action was not executed.",
    }


def execute_action(state: dict[str, Any]) -> dict[str, Any]:
    action_type = str(state.get("action_type") or "").upper().strip()
    order_id = state.get("order_id")
    amount = _safe_float(state.get("transaction_amount"))
    key = str(state.get("action_key") or "").strip()
    if not key:
        key = _make_key(action_type, order_id, state.get("customer_id"), amount)

    if action_type not in SUPPORTED_ACTIONS:
        return {
            "action_result": {
                "success": False,
                "error_code": "ACTION_NOT_SUPPORTED",
                "message": f"Action '{action_type}' is not supported.",
            },
            "status": "ACTION_FAILED",
            "resolution_success": False,
        }

    if not order_id:
        return {
            "action_result": {
                "success": False,
                "error_code": "ORDER_ID_MISSING",
                "message": "Order ID is required for this action.",
            },
            "status": "ACTION_FAILED",
            "resolution_success": False,
        }

    if action_type in FINANCIAL_ACTIONS:
        auth = _get_authorization(state)
        if auth.get("requires_human") and str(state.get("human_approval") or "").upper() != "APPROVED":
            return {
                "action_result": {
                    "success": False,
                    "error_code": "HUMAN_APPROVAL_REQUIRED",
                    "message": "Human approval is required before this transaction can execute.",
                },
                "requires_human": True,
                "authorization": auth.get("authorization"),
                "transaction_currency": auth.get("currency"),
                "human_approval_threshold": auth.get("threshold"),
                "authorization_reason": auth.get("reason", ""),
                "status": "WAITING_FOR_HUMAN_APPROVAL",
                "action_authorized": False,
            }

    executed = list(state.get("executed_action_keys") or [])
    if key in executed:
        return {
            "action_result": {
                "success": True,
                "action_type": action_type,
                "action_key": key,
                "already_executed": True,
                "message": "The action was already executed; no duplicate write was performed.",
            },
            "action_already_executed": True,
            "action_authorized": True,
            "status": "ACTION_ALREADY_EXECUTED",
        }

    if action_type == "CREATE_REFUND":
        if amount is None:
            return {
                "action_result": {
                    "success": False,
                    "error_code": "AMOUNT_MISSING",
                    "message": "A verified refund amount is required.",
                },
                "status": "ACTION_FAILED",
                "resolution_success": False,
            }
        raw = create_refund.invoke({
            "order_id": order_id,
            "amount": amount,
            "reason": state.get("issue_type", "Customer refund request"),
        })
    elif action_type == "PROCESS_RETURN":
        raw = process_return.invoke({
            "order_id": order_id,
            "reason": state.get("issue_type", "Customer return request"),
        })
    else:
        raw = cancel_order.invoke({
            "order_id": order_id,
            "reason": state.get("issue_type", "Customer cancellation request"),
        })

    success = bool(raw.get("success"))
    record = {
        "action_key": key,
        "action_type": action_type,
        "domain": state.get("domain", ""),
        "order_id": order_id,
        "customer_id": state.get("customer_id"),
        "amount": amount,
        "success": success,
        "error_code": raw.get("error_code", ""),
        "message": raw.get("message", ""),
        "raw_result": raw,
    }
    result = {
        "success": success,
        "action_type": action_type,
        "action_key": key,
        **raw,
    }
    updates: dict[str, Any] = {
        "action_result": result,
        "action_history": _history(state, record),
        "action_authorized": True,
        "resolution_success": False,
        "status": "ACTION_COMPLETED" if success else "ACTION_FAILED",
    }
    if success:
        updates["executed_action_keys"] = [*executed, key]
        updates["action_already_executed"] = False
        if raw.get("next_domain"):
            updates["next_domain"] = raw["next_domain"]
        if raw.get("amount") is not None:
            updates["transaction_amount"] = float(raw["amount"])
    else:
        updates["resolution_failure_reason"] = raw.get(
            "message",
            raw.get("error_code", "Action failed."),
        )
        if raw.get("replan") and raw.get("next_domain"):
            updates["next_domain"] = raw["next_domain"]
            updates["replan_required"] = True
    return updates
