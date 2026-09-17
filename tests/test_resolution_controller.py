from app.graph.resolution import (
    resolution_controller,
)


def test_controller_starts_with_first_unused_strategy():

    state = {
        "issue_type": "REFUND",
        "order_id": "ORD0000001",
        "transaction_amount": 1999.0,
        "attempted_strategies": [],
        "resolution_attempts": [],
    }

    result = resolution_controller(state)

    print("\nFirst attempt:")
    print(result)

    assert result["current_strategy"] == (
        "DIRECT_REFUND"
    )

    assert result["attempted_strategies"] == [
        "DIRECT_REFUND"
    ]

    assert len(
        result["resolution_attempts"]
    ) == 1


def test_controller_skips_already_attempted_strategy():

    state = {
        "issue_type": "REFUND",
        "order_id": "ORD0000001",
        "transaction_amount": 1999.0,
        "attempted_strategies": [
            "DIRECT_REFUND"
        ],
        "resolution_attempts": [],
    }

    result = resolution_controller(state)

    print("\nSecond attempt:")
    print(result)

    assert result["current_strategy"] == (
        "TRANSACTION_RECONCILIATION"
    )

    assert result["attempted_strategies"] == [
        "DIRECT_REFUND",
        "TRANSACTION_RECONCILIATION",
    ]


def test_controller_selects_third_strategy_after_two_attempts():

    state = {
        "issue_type": "REFUND",
        "order_id": "ORD0000001",
        "transaction_amount": 1999.0,
        "attempted_strategies": [
            "DIRECT_REFUND",
            "TRANSACTION_RECONCILIATION",
        ],
        "resolution_attempts": [],
    }

    result = resolution_controller(state)

    print("\nThird attempt:")
    print(result)

    assert result["current_strategy"] == (
        "RETURNLESS_ELIGIBILITY"
    )

    assert len(
        result["attempted_strategies"]
    ) == 3


def test_controller_escalates_after_all_three_attempts():

    state = {
        "issue_type": "REFUND",
        "order_id": "ORD0000001",
        "transaction_amount": 1999.0,
        "attempted_strategies": [
            "DIRECT_REFUND",
            "TRANSACTION_RECONCILIATION",
            "RETURNLESS_ELIGIBILITY",
        ],
        "resolution_attempts": [],
    }

    result = resolution_controller(state)

    print("\nAfter all three attempts:")
    print(result)

    assert result["resolution_success"] is False

    assert result["status"] == (
        "HUMAN_ESCALATION"
    )

    assert (
        "All available resolution strategies"
        in result["resolution_failure_reason"]
    )