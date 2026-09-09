from __future__ import annotations

from langchain.tools import tool

from .data_store import DataStoreError, amazon_policy, casepilot_policy


@tool
def get_amazon_policy(policy_area: str) -> dict:
    """Retrieve publicly documented Amazon policy guidance for a policy area such as returns, refunds, delivery_claims, non_returnable, returnless_resolution, or a_to_z_guarantee."""
    try:
        policy = amazon_policy()
        key = str(policy_area).strip()

        if key not in policy:
            available = [
                k for k in policy.keys()
                if k not in {"title", "source_scope"}
            ]
            return {
                "success": False,
                "error": f"Unknown policy area '{key}'.",
                "available_policy_areas": available,
            }

        return {
            "success": True,
            "policy_area": key,
            "policy": policy[key],
            "source_scope": policy.get("source_scope"),
        }
    except DataStoreError as exc:
        return {"success": False, "error": str(exc)}


@tool
def get_casepilot_policy(rule: str) -> dict:
    """Retrieve a CasePilot authorization rule such as autonomous_transaction_limit_inr, max_distinct_strategies, success_rule, failure_rule, or escalation_rule."""
    try:
        policy = casepilot_policy()
        key = str(rule).strip()

        if key not in policy:
            return {
                "success": False,
                "error": f"Unknown CasePilot policy rule '{key}'.",
                "available_rules": list(policy.keys()),
            }

        return {
            "success": True,
            "rule": key,
            "value": policy[key],
        }
    except DataStoreError as exc:
        return {"success": False, "error": str(exc)}
