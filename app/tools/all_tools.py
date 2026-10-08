from __future__ import annotations

from .read_tools import (
    get_customer_details,
    get_delivery_details,
    get_order_details,
    get_payment_details,
    get_product_details,
    get_refund_details,
    get_return_details,
)

from .policy_tools import (
    get_amazon_policy,
    get_casepilot_policy,
)

from .eligibility_tools import (
    check_refund_eligibility,
)


# ============================================================
# READ-ONLY TOOLS
# ============================================================
#
# These tools may be used by the investigation agent.
#
# IMPORTANT:
#
# No database write/action tools belong in this list.
#
# The investigation agent may:
#   - inspect operational data
#   - inspect policy
#   - check eligibility
#
# The investigation agent must NOT:
#   - create refunds
#   - cancel orders
#   - process returns
#   - modify payments
#   - perform other transactional writes
#
# Transaction execution is controlled separately by the
# LangGraph action layer.
# ============================================================

READ_ONLY_TOOLS = [
    # --------------------------------------------------------
    # RDS operational data
    # --------------------------------------------------------

    get_customer_details,
    get_order_details,
    get_payment_details,
    get_delivery_details,
    get_return_details,
    get_refund_details,
    get_product_details,

    # --------------------------------------------------------
    # S3 policy knowledge
    # --------------------------------------------------------

    get_amazon_policy,
    get_casepilot_policy,

    # --------------------------------------------------------
    # Eligibility checks
    # --------------------------------------------------------

    check_refund_eligibility,
]