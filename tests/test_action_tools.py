from app.tools.action_tools import create_refund


def test_refund_creation():

    result = create_refund.invoke({
        "order_id": "ORD0000001",
        "amount": 1999.0,
        "reason": "ORDER_CANCELLED",
    })

    print("\nRESULT:")
    print(result)


if __name__ == "__main__":
    test_refund_creation()