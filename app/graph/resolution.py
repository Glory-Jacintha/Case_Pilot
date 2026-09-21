from __future__ import annotations

from typing import Any

from app.graph.strategy_executors import execute_strategy
from app.graph.strategy_registry import get_strategies_for_domain


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
            result.get(
                "error",
                "",
            ),
        ),
        "result": result,
    }

    attempts.append(attempt)

    if strategy not in attempted:
        attempted.append(strategy)

    return attempts, attempted


def get_strategies(
    domain: str,
):
    """
    Return the strategies registered for the
    customer's current support domain.
    """

    return get_strategies_for_domain(domain)


def resolution_controller(
    state,
) -> dict[str, Any]:
    """
    Execute the next unused resolution strategy.

    Strategies are selected dynamically from the
    customer's routed domain.

    Maximum of MAX_STRATEGIES distinct strategies
    are allowed.
    """

    domain = state.get("domain")

    if not domain:
        return {
            "resolution_success": False,
            "resolution_failure_reason": (
                "A support domain is required before "
                "resolution can begin."
            ),
            "status": "HUMAN_ESCALATION",
        }

    attempted = list(
        state.get(
            "attempted_strategies",
            [],
        )
    )

    attempts = list(
        state.get(
            "resolution_attempts",
            [],
        )
    )

    try:
        strategies = get_strategies_for_domain(
            domain
        )
    except ValueError as exc:
        return {
            "resolution_success": False,
            "resolution_failure_reason": str(exc),
            "status": "HUMAN_ESCALATION",
        }

    # --------------------------------------------------
    # Enforce maximum of three distinct strategies
    # --------------------------------------------------

    if len(attempted) >= MAX_STRATEGIES:
        return {
            "resolution_success": False,
            "resolution_failure_reason": (
                "The maximum number of distinct "
                "resolution strategies has been attempted."
            ),
            "status": "HUMAN_ESCALATION",
        }

    # --------------------------------------------------
    # Find next unused strategy
    # --------------------------------------------------

    next_strategy = None

    for strategy_definition in strategies:
        strategy_name = strategy_definition["name"]

        if strategy_name not in attempted:
            next_strategy = strategy_name
            break

    # --------------------------------------------------
    # No strategies remaining
    # --------------------------------------------------

    if next_strategy is None:
        return {
            "resolution_success": False,
            "resolution_failure_reason": (
                "All available resolution strategies "
                "have already been attempted."
            ),
            "status": "HUMAN_ESCALATION",
        }

    # --------------------------------------------------
    # Execute selected strategy
    # --------------------------------------------------

    result = execute_strategy(
        next_strategy,
        state,
    )

    # --------------------------------------------------
    # Record attempt
    # --------------------------------------------------

    new_attempts, new_attempted = _record_attempt(
        state=state,
        strategy=next_strategy,
        action=next_strategy,
        result=result,
    )

    success = bool(
        result.get(
            "success",
            False,
        )
    )

    updates = {
        "current_strategy": next_strategy,
        "resolution_attempts": new_attempts,
        "attempted_strategies": new_attempted,
        "resolution_result": result,
    }

    # --------------------------------------------------
    # Strategy failed
    # --------------------------------------------------

    if not success:
        updates.update(
            {
                "resolution_success": False,
                "resolution_failure_reason": (
                    result.get(
                        "message",
                        result.get(
                            "error",
                            "Resolution strategy failed.",
                        ),
                    )
                ),
                "status": "RESOLUTION_STRATEGY_FAILED",
            }
        )

        return updates

    # --------------------------------------------------
    # Strategy succeeded technically.
    #
    # IMPORTANT:
    # The validation node still determines whether
    # the actual business outcome was achieved.
    # --------------------------------------------------

    updates.update(
        {
            "resolution_success": False,
            "action_ready": False,
            "resolution_failure_reason": "",
            "status": "RESOLUTION_PENDING_VALIDATION",
        }
    )

    return updates

# ---------------------------------------------------------
# Backward-compatible refund strategy wrappers
# ---------------------------------------------------------

def strategy_direct_refund(state) -> dict[str, Any]:
    """
    Backward-compatible wrapper for the legacy refund strategy.

    The actual strategy execution is now handled by the
    strategy executor registry.
    """
    return execute_strategy(
        "REFUND_STATUS_CHECK",
        state,
    )


def strategy_recover_transaction(state) -> dict[str, Any]:
    """
    Backward-compatible wrapper for the legacy transaction
    reconciliation strategy.
    """
    return execute_strategy(
        "REFUND_TRANSACTION_RECONCILIATION",
        state,
    )


def strategy_returnless_resolution(state) -> dict[str, Any]:
    """
    Backward-compatible wrapper for the legacy returnless
    resolution strategy.

    Returnless handling is now represented by the dynamic
    refund eligibility strategy.
    """
    return execute_strategy(
        "REFUND_ELIGIBILITY_REVIEW",
        state,
    )