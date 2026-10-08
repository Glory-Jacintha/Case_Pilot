from __future__ import annotations

from typing import Any

from app.tools.s3_policy_store import get_policy


COUNTRY_TO_CURRENCY = {
    "INDIA": "INR",
    "UNITED STATES": "USD",
    "USA": "USD",
    "US": "USD",
    "CANADA": "CAD",
    "UNITED KINGDOM": "GBP",
    "UK": "GBP",
    "AUSTRALIA": "AUD",
    "GERMANY": "EUR",
    "FRANCE": "EUR",
    "ITALY": "EUR",
    "SPAIN": "EUR",
    "NETHERLANDS": "EUR",
    "IRELAND": "EUR",
    "BELGIUM": "EUR",
    "PORTUGAL": "EUR",
    "AUSTRIA": "EUR",
    "FINLAND": "EUR",
    "GREECE": "EUR",
    "LUXEMBOURG": "EUR",
    "UNITED STATES OF AMERICA": "USD",
}


def normalize_currency(value: Any) -> str | None:
    value = str(value or "").strip().upper()
    return value or None


def currency_from_country(country: Any) -> str | None:
    value = str(country or "").strip().upper()
    return COUNTRY_TO_CURRENCY.get(value)


def get_currency_thresholds() -> dict[str, float]:
    policy = get_policy("casepilot_policy.json")
    raw = policy.get("currency_policy", {}).get("human_approval_thresholds", {})
    if not isinstance(raw, dict):
        raise ValueError("casepilot_policy.json has invalid human_approval_thresholds.")
    thresholds: dict[str, float] = {}
    for currency, threshold in raw.items():
        thresholds[str(currency).upper()] = float(threshold)
    return thresholds


def get_currency_threshold(currency: Any) -> float | None:
    normalized = normalize_currency(currency)
    if not normalized:
        return None
    return get_currency_thresholds().get(normalized)


def resolve_transaction_currency(state: dict[str, Any]) -> str | None:
    existing = normalize_currency(state.get("transaction_currency"))
    if existing:
        return existing

    evidence = state.get("evidence") or {}
    if isinstance(evidence, dict):
        for key in ("currency", "transaction_currency"):
            found = normalize_currency(evidence.get(key))
            if found:
                return found

        order = evidence.get("order")
        if isinstance(order, dict):
            found = currency_from_country(order.get("country"))
            if found:
                return found

    return None


def authorization_decision(amount: Any, currency: Any) -> dict[str, Any]:
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return {"authorization": "PENDING", "requires_human": True, "threshold": None, "reason": "A valid transaction amount is required."}

    if value < 0:
        return {"authorization": "PENDING", "requires_human": True, "threshold": None, "reason": "A transaction amount cannot be negative."}

    normalized = normalize_currency(currency)
    if not normalized:
        return {"authorization": "HUMAN_REQUIRED", "requires_human": True, "threshold": None, "reason": "Transaction currency is missing; human approval is required."}

    threshold = get_currency_threshold(normalized)
    if threshold is None:
        return {"authorization": "HUMAN_REQUIRED", "requires_human": True, "threshold": None, "reason": f"Currency {normalized} is not configured in CasePilot policy; human approval is required."}

    if value >= threshold:
        return {"authorization": "HUMAN_REQUIRED", "requires_human": True, "threshold": threshold, "reason": f"{normalized} {value:.2f} is at or above the CasePilot human-approval threshold of {normalized} {threshold:.2f}."}

    return {"authorization": "AI_ALLOWED", "requires_human": False, "threshold": threshold, "reason": f"{normalized} {value:.2f} is below the CasePilot human-approval threshold of {normalized} {threshold:.2f}."}
