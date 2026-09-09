from .read_tools import (
    get_customer_details,
    get_delivery_details,
    get_order_details,
    get_payment_details,
    get_product_details,
    get_refund_details,
    get_return_details,
)
from .policy_tools import get_amazon_policy, get_casepilot_policy
from .eligibility_tools import check_refund_eligibility


READ_ONLY_TOOLS = [
    get_customer_details,
    get_order_details,
    get_payment_details,
    get_delivery_details,
    get_return_details,
    get_refund_details,
    get_product_details,
    get_amazon_policy,
    get_casepilot_policy,
    check_refund_eligibility,
]
