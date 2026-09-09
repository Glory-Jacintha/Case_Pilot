from app.agents.agent import casepilot_agent


def run_test(question: str):
    print("\n" + "=" * 70)
    print("CUSTOMER:")
    print(question)

    result = casepilot_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": question,
                }
            ]
        }
    )

    final_message = result["messages"][-1]

    print("\nCASEPILOT:")
    
    content = final_message.content

    if isinstance(content, list):
        for block in content:
            if block.get("type") == "text":
                print(block.get("text", ""))
    else:
        print(content)

    print("=" * 70)


if __name__ == "__main__":
    run_test(
        "What is the status of order ORD0000001?"
    )