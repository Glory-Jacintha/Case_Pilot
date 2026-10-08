from __future__ import annotations

from langchain.tools import tool

from .s3_policy_store import (
    S3PolicyError,
    get_policy,
)


@tool
def get_amazon_policy(
    policy_area: str,
) -> dict:
    """
    Retrieve Amazon policy guidance from the private
    CasePilot S3 policy store.

    This tool is read-only.

    policy_area must correspond to a top-level key
    in amazon_policy.json.
    """

    try:

        policy = get_policy(
            "amazon_policy.json"
        )

        key = str(
            policy_area or ""
        ).strip()

        if not key:
            return {
                "success": False,
                "error": (
                    "A policy area is required."
                ),
            }

        if key not in policy:

            available = [
                policy_key
                for policy_key in policy.keys()
                if policy_key not in {
                    "title",
                    "source_scope",
                }
            ]

            return {
                "success": False,
                "error": (
                    f"Unknown policy area '{key}'."
                ),
                "available_policy_areas": available,
            }

        return {
            "success": True,
            "policy_source": "amazon_policy.json",
            "policy_area": key,
            "policy": policy[key],
            "source_scope": policy.get(
                "source_scope"
            ),
        }

    except S3PolicyError as exc:

        return {
            "success": False,
            "error_code": "S3_POLICY_ERROR",
            "error": str(exc),
        }

    except Exception as exc:

        return {
            "success": False,
            "error_code": "POLICY_LOOKUP_FAILED",
            "error": str(exc),
        }


@tool
def get_casepilot_policy(
    rule: str,
) -> dict:
    """
    Retrieve a CasePilot business rule from the
    private casepilot_policy.json file in S3.

    Examples of rules may include:

    - currency_policy
    - human_approval_thresholds
    - max_distinct_strategies
    - success_rule
    - failure_rule
    - escalation_rule

    The exact available rules are determined by
    the policy JSON stored in S3.
    """

    try:

        policy = get_policy(
            "casepilot_policy.json"
        )

        key = str(
            rule or ""
        ).strip()

        if not key:
            return {
                "success": False,
                "error": (
                    "A CasePilot policy rule is required."
                ),
            }

        if key not in policy:

            return {
                "success": False,
                "error": (
                    f"Unknown CasePilot policy "
                    f"rule '{key}'."
                ),
                "available_rules": list(
                    policy.keys()
                ),
            }

        return {
            "success": True,
            "policy_source": "casepilot_policy.json",
            "rule": key,
            "value": policy[key],
        }

    except S3PolicyError as exc:

        return {
            "success": False,
            "error_code": "S3_POLICY_ERROR",
            "error": str(exc),
        }

    except Exception as exc:

        return {
            "success": False,
            "error_code": "POLICY_LOOKUP_FAILED",
            "error": str(exc),
        }