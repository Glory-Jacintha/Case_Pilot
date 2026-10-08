from __future__ import annotations

from typing import Any

from app.graph.strategies import execute_strategy, get_strategies_for_domain

MAX_STRATEGIES = 3


def _record_attempt(state: dict[str, Any], strategy: str, result: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    attempts = list(state.get("resolution_attempts", []) or [])
    attempted = list(state.get("attempted_strategies", []) or [])
    attempts.append({
        "strategy": strategy,
        "action": strategy,
        "success": bool(result.get("success")),
        "error_code": result.get("error_code", ""),
        "reason": result.get("message", result.get("error", "")),
        "result": result,
        "domain": state.get("domain", ""),
    })
    if strategy not in attempted:
        attempted.append(strategy)
    return attempts, attempted


def get_strategies(domain: str):
    return get_strategies_for_domain(domain)


def resolution_controller(state: dict[str, Any]) -> dict[str, Any]:
    domain = str(state.get("domain", "")).upper().strip()
    if not domain:
        return {"resolution_success": False, "status": "HUMAN_ESCALATION", "resolution_failure_reason": "A support domain is required."}

    attempted = list(state.get("attempted_strategies", []) or [])
    # The three-strategy limit is per domain, not global across a multi-domain case.
    current_domain_attempts = [
        a for a in (state.get("resolution_attempts", []) or [])
        if str(a.get("domain", "")).upper() == domain
    ]
    attempted_for_domain = {str(a.get("strategy", "")) for a in current_domain_attempts}

    try:
        strategies = get_strategies_for_domain(domain)
    except ValueError as exc:
        return {"resolution_success": False, "status": "HUMAN_ESCALATION", "resolution_failure_reason": str(exc)}

    if len(current_domain_attempts) >= MAX_STRATEGIES:
        return {
            "resolution_success": False,
            "status": "HUMAN_ESCALATION",
            "resolution_failure_reason": f"The maximum number of distinct strategies for {domain} has been attempted.",
        }

    next_definition = next((s for s in strategies if s["name"] not in attempted_for_domain), None)
    if next_definition is None:
        return {
            "resolution_success": False,
            "status": "HUMAN_ESCALATION",
            "resolution_failure_reason": f"All available resolution strategies for {domain} have been attempted.",
        }

    strategy = next_definition["name"]
    result = execute_strategy(strategy, state)
    attempts, global_attempted = _record_attempt(state, strategy, result)

    updates: dict[str, Any] = {
        "current_strategy": strategy,
        "attempted_strategies": global_attempted,
        "resolution_attempts": attempts,
        "resolution_result": result,
        "resolution_success": False,
        "action_ready": False,
    }

    if not result.get("success"):
        updates.update({
            "resolution_failure_reason": result.get("message", result.get("error_code", "Resolution strategy failed.")),
            "status": "RESOLUTION_STRATEGY_FAILED",
        })
        return updates

    updates.update({
        "resolution_failure_reason": "",
        "status": "RESOLUTION_PENDING_VALIDATION",
    })
    return updates
