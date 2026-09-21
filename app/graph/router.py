from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

from .domains import DOMAIN_DESCRIPTIONS, SUPPORTED_DOMAINS


class RoutingDecision(BaseModel):
    domain: Literal[
        "ORDER",
        "PAYMENT",
        "DELIVERY",
        "REFUND",
        "RETURN",
        "CANCELLATION",
        "PRODUCT_QUERY",
    ] = Field(description="The primary customer-support domain.")

    issue_type: str = Field(
        description="A concise description of the customer's specific issue."
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence that the selected domain is correct."
    )

    reasoning: str = Field(
        description="Short explanation of why this domain was selected."
    )


model = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    max_retries=3,
)

router_model = model.with_structured_output(RoutingDecision)


ROUTER_PROMPT = """
You are the CasePilot customer-support routing classifier.

Classify the customer's message into exactly ONE primary domain.

Supported domains:

{domain_descriptions}

Rules:

1. Choose the domain that best represents the customer's CURRENT problem.
2. Do not choose REFUND merely because money is mentioned.
3. A question about shipment, tracking, delayed delivery, or missing delivery
   belongs to DELIVERY.
4. A question about payment transactions, failed payment, duplicate charge,
   or payment status belongs to PAYMENT.
5. A question about returning an item belongs to RETURN.
6. A question about cancelling an order belongs to CANCELLATION.
7. A question asking about an item's characteristics or information belongs
   to PRODUCT_QUERY.
8. A question about order information/status belongs to ORDER.
9. A question specifically about receiving money back/refund processing or
   refund eligibility belongs to REFUND.
10. Return ONLY one primary domain.
11. Do not invent an order ID, customer ID, amount, or other factual data.

Customer message:

{customer_message}
"""


def route_customer_message(customer_message: str) -> RoutingDecision:
    """
    Classify a customer message into one CasePilot support domain.
    """

    descriptions = "\n".join(
        f"- {domain}: {DOMAIN_DESCRIPTIONS[domain]}"
        for domain in SUPPORTED_DOMAINS
    )

    prompt = ROUTER_PROMPT.format(
        domain_descriptions=descriptions,
        customer_message=customer_message,
    )

    return router_model.invoke(prompt)