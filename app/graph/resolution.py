from __future__ import annotations

from typing import Any

from app.tools.action_tools import create_refund


MAX_STRATEGIES = 3


def _record_attempt(
    state,
    strategy: str,
    action: str,
    result: dict[str, Any],
):
    attempts = list(
        state.get("resolution_attempts", [])
    )

    attempted = list(
        state.get("attempted_strategies", [])
    )

    success = bool(
        result.get("success", False)
    )

    attempt = {
        "strategy": strategy,
        "action": action,
        "success": success,
        "error_code": result.get(
            "error_code",
            "",
        ),
        "reason": result.get(
            "message",
            "",
        ),
        "result": result,
    }

    attempts.append(attempt)

    if strategy not in attempted:
        attempted.append(strategy)

    return attempts, attempted


def strategy_direct_refund(
    state,
) -> dict[str, Any]:
    """
    Strategy 1:
    Attempt a standard direct refund.
    """

    order_id = state.get("order_id")
    amount = state.get("transaction_amount")

    if not order_id:
        return {
            "success": False,
            "error_code": "ORDER_ID_MISSING",
            "message": "Order ID is required.",
        }

    if amount is None:
        return {
            "success": False,
            "error_code": "AMOUNT_MISSING",
            "message": "Transaction amount is required.",
        }

    return create_refund.invoke(
        {
            "order_id": order_id,
            "amount": float(amount),
            "reason": "CUSTOMER_REFUND_REQUEST",
        }
    )


def strategy_recover_transaction(
    state,
) -> dict[str, Any]:
    """
    Strategy 2:
    Verify the transaction/payment relationship
    before retrying the refund operation.
    """

    order_id = state.get("order_id")

    if not order_id:
        return {
            "success": False,
            "error_code": "ORDER_ID_MISSING",
            "message": "Order ID is required.",
        }

    from app.tools.data_store import (
        orders,
        payments,
        refunds,
    )

    order = next(
        (
            row
            for row in orders()
            if row["OrderID"] == order_id
        ),
        None,
    )

    payment = next(
        (
            row
            for row in payments()
            if row["OrderID"] == order_id
        ),
        None,
    )

    refund = next(
        (
            row
            for row in refunds()
            if row["OrderID"] == order_id
        ),
        None,
    )

    if not order:
        return {
            "success": False,
            "error_code": "ORDER_NOT_FOUND",
            "message": (
                f"Order {order_id} could not be found."
            ),
        }

    if not payment:
        return {
            "success": False,
            "error_code": "PAYMENT_NOT_FOUND",
            "message": (
                "No payment record was found."
            ),
        }

    if payment.get("PaymentStatus") != "SUCCESS":
        return {
            "success": False,
            "error_code": "PAYMENT_NOT_SUCCESSFUL",
            "message": (
                "The original payment was not successful."
            ),
        }

    if not refund:
        return {
            "success": False,
            "error_code": "REFUND_RECORD_NOT_FOUND",
            "message": (
                "No existing refund record was found."
            ),
        }

    return {
        "success": True,
        "error_code": "",
        "message": (
            "Payment and refund records were "
            "successfully reconciled."
        ),
        "operation": "TRANSACTION_RECONCILIATION",
        "order_id": order_id,
        "transaction_id": payment.get(
            "TransactionID"
        ),
        "refund_id": refund.get(
            "RefundID"
        ),
        "refund_status": refund.get(
            "RefundStatus"
        ),
    }


def strategy_returnless_resolution(
    state,
) -> dict[str, Any]:
    """
    Strategy 3:
    Check whether a returnless resolution is
    applicable.

    This does NOT automatically issue a refund.
    """

    order_id = state.get("order_id")

    if not order_id:
        return {
            "success": False,
            "error_code": "ORDER_ID_MISSING",
            "message": "Order ID is required.",
        }

    from app.tools.data_store import (
        orders,
        products,
    )

    order = next(
        (
            row
            for row in orders()
            if row["OrderID"] == order_id
        ),
        None,
    )

    if not order:
        return {
            "success": False,
            "error_code": "ORDER_NOT_FOUND",
            "message": (
                f"Order {order_id} could not be found."
            ),
        }

    product_id = order.get("ProductID")

    product = next(
        (
            row
            for row in products()
            if row["ProductID"] == product_id
        ),
        None,
    )

    if not product:
        return {
            "success": False,
            "error_code": "PRODUCT_NOT_FOUND",
            "message": (
                "Product information could not be found."
            ),
        }

    # We deliberately do not automatically approve
    # a returnless refund.
    return {
        "success": False,
        "error_code": "RETURNLESS_NOT_AUTOMATIC",
        "message": (
            "Returnless resolution requires "
            "additional eligibility checks."
        ),
        "operation": "RETURNLESS_ELIGIBILITY_CHECK",
        "order_id": order_id,
        "product_id": product_id,
    }


def get_strategies(
    issue_type: str,
):
    """
    Select distinct strategies based on issue type.
    """

    issue = (issue_type or "").upper()

    if "REFUND" in issue:
        return [
            (
                "DIRECT_REFUND",
                strategy_direct_refund,
            ),
            (
                "TRANSACTION_RECONCILIATION",
                strategy_recover_transaction,
            ),
            (
                "RETURNLESS_ELIGIBILITY",
                strategy_returnless_resolution,
            ),
        ]
    # ---------------------------------------------------------
    # These will be implemented next.
    # Do NOT execute refund strategies for other domains.
    # ---------------------------------------------------------
    return []

def resolution_controller(state) -> dict[str, Any]:
    """
    Execute the next unused resolution strategy.

    Maximum of MAX_STRATEGIES distinct strategies are allowed.
    """

    issue_type = state.get("issue_type", "")

    attempted = list(
        state.get("attempted_strategies", [])
    )

    attempts = list(
        state.get("resolution_attempts", [])
    )

    strategies = get_strategies(issue_type)

    # ---------------------------------------------------------
    # Find the next unused strategy
    # ---------------------------------------------------------

    next_strategy = None
    strategy_function = None

    for strategy_name, function in strategies:

        if strategy_name not in attempted:

            next_strategy = strategy_name
            strategy_function = function
            break

    # ---------------------------------------------------------
    # No strategies remaining
    # ---------------------------------------------------------

    if next_strategy is None:

        return {
            "resolution_success": False,
            "resolution_failure_reason": (
                "All available resolution strategies "
                "have already been attempted."
            ),
            "status": "HUMAN_ESCALATION",
        }

    # ---------------------------------------------------------
    # Execute strategy
    # ---------------------------------------------------------

    try:

        result = strategy_function(state)

    except Exception as exc:

        result = {
            "success": False,
            "error_code": "STRATEGY_EXECUTION_ERROR",
            "message": str(exc),
        }

    # ---------------------------------------------------------
    # Record attempt
    # ---------------------------------------------------------

    new_attempts, new_attempted = _record_attempt(
        state=state,
        strategy=next_strategy,
        action=next_strategy,
        result=result,
    )

    success = bool(
        result.get("success", False)
    )

    updates = {
        "current_strategy": next_strategy,
        "resolution_attempts": new_attempts,
        "attempted_strategies": new_attempted,
        "resolution_result": result,
    }

    # ---------------------------------------------------------
    # Strategy itself failed
    # ---------------------------------------------------------

    if not success:

        updates.update(
            {
                "resolution_success": False,
                "resolution_failure_reason": (
                    result.get(
                        "message",
                        "Resolution strategy failed.",
                    )
                ),
                "status": "RESOLUTION_STRATEGY_FAILED",
            }
        )

        return updates

    # ---------------------------------------------------------
    # Strategy succeeded technically.
    #
    # IMPORTANT:
    # We still validate the actual business outcome.
    # ---------------------------------------------------------

    updates.update(
        {
            "resolution_success": False,
            "resolution_failure_reason": "",
            "status": "RESOLUTION_PENDING_VALIDATION",
        }
    )

    return updates