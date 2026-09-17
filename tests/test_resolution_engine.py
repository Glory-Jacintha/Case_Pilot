from app.graph.resolution import (
    get_strategies,
    strategy_direct_refund,
    strategy_recover_transaction,
    strategy_returnless_resolution,
)


def test_refund_has_three_distinct_strategies():

    strategies = get_strategies("REFUND")

    names = [
        name
        for name, _ in strategies
    ]

    assert len(names) == 3

    assert len(set(names)) == 3

    assert names == [
        "DIRECT_REFUND",
        "TRANSACTION_RECONCILIATION",
        "RETURNLESS_ELIGIBILITY",
    ]


def test_non_refund_does_not_use_refund_strategies():

    strategies = get_strategies("DELIVERY")

    assert strategies == []


def test_direct_refund_requires_order():

    result = strategy_direct_refund(
        {
            "transaction_amount": 1999.0,
        }
    )

    assert result["success"] is False
    assert result["error_code"] == "ORDER_ID_MISSING"


def test_direct_refund_requires_amount():

    result = strategy_direct_refund(
        {
            "order_id": "ORD0000001",
        }
    )

    assert result["success"] is False
    assert result["error_code"] == "AMOUNT_MISSING"


def test_transaction_reconciliation_requires_order():

    result = strategy_recover_transaction({})

    assert result["success"] is False
    assert result["error_code"] == "ORDER_ID_MISSING"


def test_returnless_requires_order():

    result = strategy_returnless_resolution({})

    assert result["success"] is False
    assert result["error_code"] == "ORDER_ID_MISSING"