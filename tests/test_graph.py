from app.graph.graph import casepilot_graph


if __name__ == "__main__":

    customer_message = """
    What is the status of order ORD0000001?
    """

    result = casepilot_graph.invoke(
        {
            "customer_message": customer_message
        }
    )

    print()
    print("=" * 70)
    print("CASEPILOT INVESTIGATION")
    print("=" * 70)

    print("\nCUSTOMER MESSAGE:")
    print(customer_message.strip())

    print("\nINVESTIGATION:")
    print(result.get("investigation", "No investigation"))

    print("\nTRANSACTION AMOUNT:")
    print(result.get("transaction_amount", "Not found"))

    print("\nAUTHORIZATION:")
    print(result.get("authorization", "Not determined"))

    print("\nREQUIRES HUMAN:")
    print(result.get("requires_human", "Not determined"))

    print("\nSTATUS:")
    print(result.get("status", "Unknown"))

    print("=" * 70)