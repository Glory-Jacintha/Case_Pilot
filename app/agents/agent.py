import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from app.tools.all_tools import READ_ONLY_TOOLS


# Load environment variables from .env
load_dotenv()


# --------------------------------------------------
# 1. Create Gemini model
# --------------------------------------------------

model = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    temperature=0,
    max_retries=3,
)


# --------------------------------------------------
# 2. CasePilot system instructions
# --------------------------------------------------

SYSTEM_PROMPT = """
You are CasePilot, an e-commerce customer support investigation agent.

Your job in this phase is INVESTIGATION ONLY.

Use the available read-only tools to investigate the customer's issue.

You may inspect:
- customer information
- order information
- payment information
- delivery information
- return information
- refund information
- product information
- Amazon public policy guidance
- CasePilot business policy

Do NOT perform refunds, cancellations, replacements, or any other transaction.

Do NOT invent information.

When investigating an order-related issue, determine the relevant
transaction/order amount from the available data.

At the end of every investigation, provide a concise summary.

IMPORTANT:
The final response MUST contain this exact field:

TRANSACTION_AMOUNT: <amount>

For example:

TRANSACTION_AMOUNT: 1999.00

If you cannot determine the transaction amount from the available
information, write:

TRANSACTION_AMOUNT: UNKNOWN

Also explain the important evidence you found.
"""

# --------------------------------------------------
# 3. Create CasePilot agent
# --------------------------------------------------

casepilot_agent = create_agent(
    model=model,
    tools=READ_ONLY_TOOLS,
    system_prompt=SYSTEM_PROMPT,
    name="casepilot_agent",
)