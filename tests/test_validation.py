from app.graph import validation


# ---------------------------------------------------------
# Test data used only by these tests
# ---------------------------------------------------------

ORDER_ROWS = [
    {
        "OrderID": "ORD0000001",
        "TotalAmount": "1999",
    }
]

PAYMENT_ROWS = [
    {
        "OrderID": "ORD0000001",
        "PaymentStatus": "SUCCESS",
    }
]


def setup_fake_data(monkeypatch, refund_status):
    """
    Replace the real CSV data functions with small
    in-memory test records.

    This means the tests do NOT modify refunds.csv.
    """

    REFUND_ROWS = [
        {
            "OrderID": "ORD0000001",
            "RefundID": "REF00000001",
            "RefundAmount": "1999",
            "RefundStatus": refund_status,
        }
    ]

    monkeypatch.setattr(
        validation,
        "orders",
        lambda: ORDER_ROWS,
    )

    monkeypatch.setattr(
        validation,
        "payments",
        lambda: PAYMENT_ROWS,
    )

    monkeypatch.setattr(
        validation,
        "refunds",
        lambda: REFUND_ROWS,
    )


# =========================================================
# 1. COMPLETED refund
# =========================================================

def test_completed_refund_resolves_customer_issue(
    monkeypatch,
):

    setup_fake_data(
        monkeypatch,
        "COMPLETED",
    )

    state = {
        "issue_type": "REFUND",
        "order_id": "ORD0000001",
        "customer_message": (
            "I haven't received my refund."
        ),
    }

    result = validation.validate_resolution(
        state
    )

    print("\nCOMPLETED refund:")
    print(result)

    assert result["resolution_success"] is True

    assert result["status"] == (
        "RESOLUTION_COMPLETED"
    )

    assert result["resolution_result"][
        "refund_status"
    ] == "COMPLETED"


# =========================================================
# 2. PROCESSING refund
# =========================================================

def test_processing_refund_does_not_resolve_customer_issue(
    monkeypatch,
):

    setup_fake_data(
        monkeypatch,
        "PROCESSING",
    )

    state = {
        "issue_type": "REFUND",
        "order_id": "ORD0000001",
        "customer_message": (
            "I haven't received my refund."
        ),
    }

    result = validation.validate_resolution(
        state
    )

    print("\nPROCESSING refund:")
    print(result)

    assert result["resolution_success"] is False

    assert result["status"] == (
        "RESOLUTION_VALIDATION_FAILED"
    )

    assert "PROCESSING" in (
        result["resolution_failure_reason"]
    )


# =========================================================
# 3. No refund record
# =========================================================

def test_missing_refund_record_fails_validation(
    monkeypatch,
):

    monkeypatch.setattr(
        validation,
        "orders",
        lambda: ORDER_ROWS,
    )

    monkeypatch.setattr(
        validation,
        "payments",
        lambda: PAYMENT_ROWS,
    )

    monkeypatch.setattr(
        validation,
        "refunds",
        lambda: [],
    )

    state = {
        "issue_type": "REFUND",
        "order_id": "ORD0000001",
        "customer_message": (
            "I haven't received my refund."
        ),
    }

    result = validation.validate_resolution(
        state
    )

    print("\nMissing refund:")
    print(result)

    assert result["resolution_success"] is False

    assert result["status"] == (
        "RESOLUTION_VALIDATION_FAILED"
    )

    assert "No refund record exists" in (
        result["resolution_failure_reason"]
    )


# =========================================================
# 4. Missing order ID
# =========================================================

def test_missing_order_id_fails_validation():

    state = {
        "issue_type": "REFUND",
        "customer_message": (
            "I haven't received my refund."
        ),
    }

    result = validation.validate_resolution(
        state
    )

    print("\nMissing order ID:")
    print(result)

    assert result["resolution_success"] is False

    assert result["status"] == (
        "RESOLUTION_VALIDATION_FAILED"
    )

    assert "Order ID is required" in (
        result["resolution_failure_reason"]
    )


# =========================================================
# 5. Non-refund generic successful resolution
# =========================================================

def test_generic_successful_resolution():

    state = {
        "issue_type": "DELIVERY",
        "order_id": "ORD0000001",
        "resolution_result": {
            "success": True,
            "operation": "DELIVERY_RESOLVED",
        },
    }

    result = validation.validate_resolution(
        state
    )

    print("\nGeneric successful resolution:")
    print(result)

    assert result["resolution_success"] is True

    assert result["status"] == (
        "RESOLUTION_COMPLETED"
    )


# =========================================================
# 6. Non-refund generic failed resolution
# =========================================================

def test_generic_failed_resolution():

    state = {
        "issue_type": "DELIVERY",
        "order_id": "ORD0000001",
        "resolution_result": {
            "success": False,
            "error_code": "TRACKING_UNAVAILABLE",
        },
    }

    result = validation.validate_resolution(
        state
    )

    print("\nGeneric failed resolution:")
    print(result)

    assert result["resolution_success"] is False

    assert result["status"] == (
        "RESOLUTION_VALIDATION_FAILED"
    )