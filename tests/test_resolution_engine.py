from app.graph.resolution import get_strategies
from app.graph.strategy_executors import STRATEGY_EXECUTORS


def test_refund_has_three_distinct_strategies():

    strategies = get_strategies("REFUND")

    names = [
        strategy["name"]
        for strategy in strategies
    ]

    assert len(names) == 3

    assert len(set(names)) == 3

    assert names == [
        "REFUND_STATUS_CHECK",
        "REFUND_TRANSACTION_RECONCILIATION",
        "REFUND_ELIGIBILITY_REVIEW",
    ]


def test_all_supported_domains_have_three_strategies():

    expected_domains = [
        "ORDER",
        "PAYMENT",
        "DELIVERY",
        "REFUND",
        "RETURN",
        "CANCELLATION",
        "PRODUCT_QUERY",
    ]

    for domain in expected_domains:

        strategies = get_strategies(domain)

        assert len(strategies) == 3

        names = [
            strategy["name"]
            for strategy in strategies
        ]

        assert len(set(names)) == 3


def test_all_registered_strategies_have_executors():

    for domain in [
        "ORDER",
        "PAYMENT",
        "DELIVERY",
        "REFUND",
        "RETURN",
        "CANCELLATION",
        "PRODUCT_QUERY",
    ]:

        strategies = get_strategies(domain)

        for strategy in strategies:

            assert strategy["name"] in (
                STRATEGY_EXECUTORS
            )


def test_invalid_domain_is_rejected():

    try:
        get_strategies("INVALID_DOMAIN")
    except ValueError as exc:
        assert "Unsupported CasePilot domain" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for invalid domain."
        )