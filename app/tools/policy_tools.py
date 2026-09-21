from __future__ import annotations

from langchain.tools import tool

from .s3_policy_store import S3PolicyError, get_policy


@tool
def get_amazon_policy(policy_area: str) -> dict:
    """
    Retrieve publicly documented Amazon policy guidance for a
    specific policy area.
    """

    try:
        policy = get_policy("amazon_policy.json")
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

    except S3PolicyError as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def get_casepilot_policy(rule: str) -> dict:
    """
    Retrieve a CasePilot business rule such as
    autonomous_transaction_limit_inr, max_distinct_strategies,
    success_rule, failure_rule, or escalation_rule.
    """

    try:
        policy = get_policy("casepilot_policy.json")
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

    except S3PolicyError as exc:
        return {
            "success": False,
            "error": str(exc),
        }