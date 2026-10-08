from __future__ import annotations

from datetime import date, datetime, timedelta

from langchain.tools import tool

from app.db.postgres import DatabaseError, fetch_all, fetch_one
from app.tools.s3_policy_store import (
    S3PolicyError,
    get_policy,
)


def _parse_date(value: str) -> date | None:
    """
    Parse supported request-date formats.

    Supported formats:
    - YYYY-MM-DD
    - DD-MM-YYYY
    - DD/MM/YYYY
    """

    value = str(value or "").strip()

    if not value:
        return None

    for fmt in (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(
                value,
                fmt,
            ).date()
        except ValueError:
            continue

    return None


def _normalise_status(value) -> str:
    """
    Normalize a database status value.
    """

    return str(value or "").strip().upper()


def _safe_amount(value) -> float | None:
    """
    Safely convert a database amount into float.
    """

    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None

    if amount != amount:
        return None

    return amount


def _normalise_order_date(value) -> date | None:
    """
    Convert a PostgreSQL date/datetime value to date.
    """

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if value is None:
        return None

    if isinstance(value, str):
        return _parse_date(value)

    return None


def _load_policies() -> tuple[dict, dict]:
    """
    Load the two authoritative CasePilot policy files from S3.

    Returns:

        amazon_policy
        casepilot_policy
    """

    amazon_policy = get_policy(
        "amazon_policy.json"
    )

    casepilot_policy = get_policy(
        "casepilot_policy.json"
    )

    return (
        amazon_policy,
        casepilot_policy,
    )


def _get_policy_return_window(
    amazon_policy: dict,
) -> int | None:
    """
    Extract a general return-window value only if one is
    explicitly present in the Amazon policy.

    The supplied Amazon policy does NOT currently provide a
    numeric universal return window. Therefore this function
    normally returns None.

    Product-specific return_window_days comes from RDS product
    metadata and should be used when available.
    """

    returns_policy = amazon_policy.get(
        "returns",
        {},
    )

    if not isinstance(
        returns_policy,
        dict,
    ):
        return None

    value = returns_policy.get(
        "return_window_days"
    )

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _get_policy_verification_checks(
    amazon_policy: dict,
) -> list[str]:
    """
    Retrieve the refund verification checks defined by
    Amazon policy.
    """

    refunds_policy = amazon_policy.get(
        "refunds",
        {},
    )

    if not isinstance(
        refunds_policy,
        dict,
    ):
        return []

    checks = refunds_policy.get(
        "verification",
        [],
    )

    if not isinstance(
        checks,
        list,
    ):
        return []

    return [
        str(check).strip()
        for check in checks
        if str(check).strip()
    ]


def _is_exception_guidance_available(
    amazon_policy: dict,
) -> bool:
    """
    Determine whether the Amazon policy provides
    exception guidance for non-returnable products.
    """

    non_returnable = amazon_policy.get(
        "non_returnable",
        {},
    )

    if not isinstance(
        non_returnable,
        dict,
    ):
        return False

    return bool(
        str(
            non_returnable.get(
                "exception_guidance",
                "",
            )
        ).strip()
    )


def _build_policy_evidence(
    amazon_policy: dict,
    casepilot_policy: dict,
) -> dict:
    """
    Build a structured policy-evidence object.

    This does not make an eligibility decision.
    """

    refunds_policy = amazon_policy.get(
        "refunds",
        {},
    )

    returns_policy = amazon_policy.get(
        "returns",
        {},
    )

    non_returnable_policy = amazon_policy.get(
        "non_returnable",
        {},
    )

    returnless_policy = amazon_policy.get(
        "returnless_resolution",
        {},
    )

    return {
        "amazon_policy": {
            "returns_guidance": (
                returns_policy.get(
                    "general_guidance"
                )
                if isinstance(
                    returns_policy,
                    dict,
                )
                else None
            ),
            "returns_rule": (
                returns_policy.get(
                    "rule"
                )
                if isinstance(
                    returns_policy,
                    dict,
                )
                else None
            ),
            "non_returnable_examples": (
                non_returnable_policy.get(
                    "examples",
                    [],
                )
                if isinstance(
                    non_returnable_policy,
                    dict,
                )
                else []
            ),
            "non_returnable_exception_guidance": (
                non_returnable_policy.get(
                    "exception_guidance"
                )
                if isinstance(
                    non_returnable_policy,
                    dict,
                )
                else None
            ),
            "returnless_guidance": (
                returnless_policy.get(
                    "guidance"
                )
                if isinstance(
                    returnless_policy,
                    dict,
                )
                else None
            ),
            "returnless_rule": (
                returnless_policy.get(
                    "rule"
                )
                if isinstance(
                    returnless_policy,
                    dict,
                )
                else None
            ),
            "refund_guidance": (
                refunds_policy.get(
                    "seller_fulfilled_guidance"
                )
                if isinstance(
                    refunds_policy,
                    dict,
                )
                else None
            ),
            "refund_verification_checks": (
                _get_policy_verification_checks(
                    amazon_policy
                )
            ),
        },
        "casepilot_policy": {
            "currency_policy": casepilot_policy.get(
                "currency_policy"
            ),
            "human_approval_thresholds": (
                casepilot_policy.get(
                    "currency_policy", {}
                ).get(
                    "human_approval_thresholds", {}
                )
            ),
            "human_approval_rule": (
                casepilot_policy.get(
                    "human_approval_rule"
                )
            ),
            "ai_resolution_rule": (
                casepilot_policy.get(
                    "ai_resolution_rule"
                )
            ),
        },
    }


@tool
def check_refund_eligibility(
    order_id: str,
    request_date: str = "",
) -> dict:
    """
    Determine whether the available operational data and
    applicable S3 policy information support a refund action.

    SOURCE OF TRUTH:

    PostgreSQL/RDS:
        - order
        - payment
        - product
        - return
        - refund

    S3:
        - amazon_policy.json
        - casepilot_policy.json

    IMPORTANT:

    This tool is READ-ONLY.

    It does NOT:
        - create a refund
        - update a refund
        - modify an order
        - modify a return
        - modify a payment

    Authorization is deliberately separate from eligibility.

    A case can be:

        eligible = True
        authorization = HUMAN_REQUIRED

    when the refund is eligible but the transaction amount
    reaches CasePilot's human-approval threshold.
    """

    order_id = str(
        order_id or ""
    ).strip()

    if not order_id:
        return {
            "success": False,
            "eligible": False,
            "error_code": "ORDER_ID_REQUIRED",
            "reason": (
                "An order ID is required."
            ),
        }

    try:

        # =========================================================
        # 1. LOAD AUTHORITATIVE POLICIES FROM S3
        # =========================================================

        (
            amazon_policy,
            casepilot_policy,
        ) = _load_policies()

        policy_evidence = _build_policy_evidence(
            amazon_policy=amazon_policy,
            casepilot_policy=casepilot_policy,
        )

        refund_verification_checks = (
            _get_policy_verification_checks(
                amazon_policy
            )
        )

        # =========================================================
        # 2. FIND ORDER
        # =========================================================

        order = fetch_one(
            """
            SELECT
                order_id,
                order_date,
                customer_id,
                product_id,
                total_amount,
                order_status
            FROM orders
            WHERE order_id = %s
            """,
            (order_id,),
        )

        if not order:
            return {
                "success": False,
                "eligible": False,
                "error_code": "ORDER_NOT_FOUND",
                "order_id": order_id,
                "reason": (
                    f"Order {order_id} was not found."
                ),
                "policy_sources": [
                    "amazon_policy.json",
                    "casepilot_policy.json",
                ],
            }

        # =========================================================
        # 3. VALIDATE ORDER AMOUNT
        # =========================================================

        order_amount = _safe_amount(
            order.get("total_amount")
        )

        if order_amount is None:
            return {
                "success": False,
                "eligible": False,
                "error_code": "INVALID_ORDER_AMOUNT",
                "order_id": order_id,
                "reason": (
                    "The order amount could not be determined."
                ),
                "policy_evidence": policy_evidence,
            }

        # =========================================================
        # 4. FIND PAYMENT
        # =========================================================

        payment = fetch_one(
            """
            SELECT
                transaction_id,
                amount,
                payment_status,
                gateway_reference
            FROM payments
            WHERE order_id = %s
            ORDER BY transaction_date DESC
            LIMIT 1
            """,
            (order_id,),
        )

        payment_exists = payment is not None

        if not payment:
            return {
                "success": True,
                "eligible": False,
                "order_id": order_id,
                "amount": order_amount,
                "reason": (
                    "No payment record exists for the order."
                ),
                "checks": {
                    "order_verified": True,
                    "payment_verified": False,
                    "payment_successful": False,
                },
                "policy_checks_required": (
                    refund_verification_checks
                ),
                "policy_evidence": policy_evidence,
                "policy_sources": [
                    "amazon_policy.json",
                    "casepilot_policy.json",
                ],
            }

        payment_status = _normalise_status(
            payment.get("payment_status")
        )

        # =========================================================
        # 5. PAYMENT MUST BE SUCCESSFUL
        # =========================================================

        if payment_status != "SUCCESS":
            return {
                "success": True,
                "eligible": False,
                "order_id": order_id,
                "amount": order_amount,
                "payment_status": payment_status,
                "reason": (
                    f"Payment status is "
                    f"{payment_status or 'UNKNOWN'}, "
                    "not SUCCESS."
                ),
                "checks": {
                    "order_verified": True,
                    "payment_verified": payment_exists,
                    "payment_successful": False,
                },
                "policy_checks_required": (
                    refund_verification_checks
                ),
                "policy_evidence": policy_evidence,
                "policy_sources": [
                    "amazon_policy.json",
                    "casepilot_policy.json",
                ],
            }

        # =========================================================
        # 6. FIND EXISTING REFUNDS
        # =========================================================

        refund_records = fetch_all(
            """
            SELECT
                refund_id,
                refund_amount,
                refund_status,
                refund_reason,
                requested_date,
                processed_date
            FROM refunds
            WHERE order_id = %s
            ORDER BY requested_date DESC NULLS LAST
            """,
            (order_id,),
        )

        completed_refund = None
        processing_refund = None
        not_initiated_refund = None

        for refund in refund_records:

            refund_status = _normalise_status(
                refund.get("refund_status")
            )

            if (
                refund_status == "COMPLETED"
                and completed_refund is None
            ):
                completed_refund = refund

            elif (
                refund_status == "PROCESSING"
                and processing_refund is None
            ):
                processing_refund = refund

            elif (
                refund_status == "NOT_INITIATED"
                and not_initiated_refund is None
            ):
                not_initiated_refund = refund

        # =========================================================
        # 7. COMPLETED REFUND
        # =========================================================

        if completed_refund:

            return {
                "success": True,
                "eligible": False,
                "order_id": order_id,
                "amount": order_amount,
                "refund_id": completed_refund.get(
                    "refund_id"
                ),
                "refund_status": "COMPLETED",
                "reason": (
                    "A completed refund already exists "
                    "for this order."
                ),
                "checks": {
                    "order_verified": True,
                    "payment_successful": True,
                    "refund_already_exists": True,
                    "completed_refund": True,
                },
                "policy_checks_required": (
                    refund_verification_checks
                ),
                "policy_evidence": policy_evidence,
                "policy_sources": [
                    "amazon_policy.json",
                    "casepilot_policy.json",
                ],
            }

        # =========================================================
        # 8. PROCESSING REFUND
        # =========================================================

        if processing_refund:

            processing_amount = _safe_amount(
                processing_refund.get(
                    "refund_amount"
                )
            )

            return {
                "success": True,
                "eligible": False,
                "order_id": order_id,
                "amount": order_amount,
                "refund_id": processing_refund.get(
                    "refund_id"
                ),
                "refund_status": "PROCESSING",
                "refund_amount": processing_amount,
                "reason": (
                    "A refund is already being processed "
                    "for this order."
                ),
                "checks": {
                    "order_verified": True,
                    "payment_successful": True,
                    "refund_already_exists": True,
                    "processing_refund": True,
                },
                "policy_checks_required": (
                    refund_verification_checks
                ),
                "policy_evidence": policy_evidence,
                "policy_sources": [
                    "amazon_policy.json",
                    "casepilot_policy.json",
                ],
            }

        # =========================================================
        # 9. FIND PRODUCT
        # =========================================================

        product_id = str(
            order.get("product_id") or ""
        ).strip()

        product = None

        if product_id:

            product = fetch_one(
                """
                SELECT
                    product_id,
                    product_name,
                    category,
                    brand,
                    return_window_days,
                    return_eligible,
                    returnless_refund_eligible,
                    non_returnable_reason
                FROM products
                WHERE product_id = %s
                """,
                (product_id,),
            )

        # =========================================================
        # 10. PRODUCT INFORMATION
        # =========================================================

        if not product:

            return {
                "success": True,
                "eligible": False,
                "order_id": order_id,
                "amount": order_amount,
                "product_id": product_id,
                "reason": (
                    "The product associated with the order "
                    "could not be found, so the applicable "
                    "product/category refund eligibility "
                    "could not be verified."
                ),
                "checks": {
                    "order_verified": True,
                    "payment_successful": True,
                    "product_verified": False,
                },
                "policy_evidence": policy_evidence,
                "policy_sources": [
                    "amazon_policy.json",
                    "casepilot_policy.json",
                ],
            }

        # =========================================================
        # 11. FIND RETURN
        # =========================================================

        return_record = fetch_one(
            """
            SELECT
                return_id,
                return_status,
                return_reason,
                requested_date,
                approved_date
            FROM returns
            WHERE order_id = %s
            ORDER BY requested_date DESC NULLS LAST
            LIMIT 1
            """,
            (order_id,),
        )

        return_status = _normalise_status(
            return_record.get(
                "return_status"
            )
            if return_record
            else ""
        )

        # =========================================================
        # 12. PRODUCT RETURNABILITY
        # =========================================================

        product_return_eligible = (
            product.get("return_eligible")
        )

        product_returnless_eligible = (
            product.get(
                "returnless_refund_eligible"
            )
        )

        non_returnable_reason = str(
            product.get(
                "non_returnable_reason"
            )
            or ""
        ).strip()

        # ---------------------------------------------------------
        # Explicitly non-returnable
        #
        # Amazon policy says some exceptions may still qualify
        # for refund/replacement when damaged, defective, or
        # materially different.
        #
        # We do NOT have enough information in this tool input
        # to establish such an exception.
        # ---------------------------------------------------------

        if product_return_eligible is False:

            exception_guidance_available = (
                _is_exception_guidance_available(
                    amazon_policy
                )
            )

            return {
                "success": True,
                "eligible": False,
                "order_id": order_id,
                "amount": order_amount,
                "product_id": product_id,
                "reason": (
                    "The product is marked non-returnable "
                    "in the operational product data. "
                    "Amazon policy provides possible exception "
                    "guidance, but this eligibility check does "
                    "not have sufficient evidence to establish "
                    "an exception."
                ),
                "exception_check_required": (
                    exception_guidance_available
                ),
                "non_returnable_reason": (
                    non_returnable_reason
                ),
                "checks": {
                    "order_verified": True,
                    "payment_successful": True,
                    "product_verified": True,
                    "product_return_eligible": False,
                    "exception_verified": False,
                },
                "policy_evidence": policy_evidence,
                "policy_sources": [
                    "amazon_policy.json",
                    "casepilot_policy.json",
                ],
            }

        # =========================================================
        # 13. RETURN-WINDOW CHECK
        # =========================================================

        return_window = None

        if product.get(
            "return_window_days"
        ) is not None:

            try:
                return_window = int(
                    product.get(
                        "return_window_days"
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                return_window = None

        # The Amazon policy supplied by the user does not define
        # a numeric universal return window.
        #
        # Therefore:
        #
        #   product.return_window_days
        #
        # is used when available.
        #
        # We do NOT silently replace it with 30 days.

        if request_date:

            requested_date = _parse_date(
                request_date
            )

            order_date = _normalise_order_date(
                order.get("order_date")
            )

            if requested_date is None:

                return {
                    "success": True,
                    "eligible": False,
                    "order_id": order_id,
                    "amount": order_amount,
                    "reason": (
                        "The supplied request date could "
                        "not be parsed."
                    ),
                    "checks": {
                        "order_verified": True,
                        "payment_successful": True,
                        "return_window_checked": False,
                    },
                    "policy_evidence": policy_evidence,
                }

            if order_date is None:

                return {
                    "success": True,
                    "eligible": False,
                    "order_id": order_id,
                    "amount": order_amount,
                    "reason": (
                        "The order date could not be determined, "
                        "so the applicable product return "
                        "window could not be evaluated."
                    ),
                    "checks": {
                        "order_verified": True,
                        "payment_successful": True,
                        "return_window_checked": False,
                    },
                    "policy_evidence": policy_evidence,
                }

            if return_window is None:

                # We have Amazon's rule saying to check the
                # applicable product/category window, but no
                # numeric value was supplied by the policy.
                #
                # If product data also lacks a window, do not
                # invent 30 days.

                policy_window = (
                    _get_policy_return_window(
                        amazon_policy
                    )
                )

                if policy_window is not None:
                    return_window = policy_window

            if return_window is not None:

                deadline = (
                    order_date
                    + timedelta(
                        days=return_window
                    )
                )

                if requested_date > deadline:

                    return {
                        "success": True,
                        "eligible": False,
                        "order_id": order_id,
                        "amount": order_amount,
                        "reason": (
                            f"The request is outside the "
                            f"applicable {return_window}-day "
                            "return window."
                        ),
                        "request_date": (
                            requested_date.isoformat()
                        ),
                        "return_window_days": (
                            return_window
                        ),
                        "deadline": (
                            deadline.isoformat()
                        ),
                        "checks": {
                            "order_verified": True,
                            "payment_successful": True,
                            "return_window_checked": True,
                            "within_return_window": False,
                        },
                        "policy_evidence": (
                            policy_evidence
                        ),
                        "policy_sources": [
                            "amazon_policy.json",
                            "casepilot_policy.json",
                        ],
                    }

        # =========================================================
        # 14. RETURN RECEIPT CHECK
        # =========================================================

        order_status = _normalise_status(
            order.get("order_status")
        )

        return_received = (
            return_status in {
                "RECEIVED",
                "COMPLETED",
            }
        )

        # Amazon policy says return receipt should be checked
        # where applicable.

        return_receipt_required = (
            order_status == "RETURNED"
            or return_record is not None
        )

        if return_receipt_required:

            if not return_record:

                return {
                    "success": True,
                    "eligible": False,
                    "order_id": order_id,
                    "amount": order_amount,
                    "reason": (
                        "A return is relevant to this refund "
                        "case, but no return record was found."
                    ),
                    "checks": {
                        "order_verified": True,
                        "payment_successful": True,
                        "return_record_exists": False,
                        "return_receipt_checked": False,
                    },
                    "policy_evidence": (
                        policy_evidence
                    ),
                    "policy_sources": [
                        "amazon_policy.json",
                        "casepilot_policy.json",
                    ],
                }

            if not return_received:

                return {
                    "success": True,
                    "eligible": False,
                    "order_id": order_id,
                    "amount": order_amount,
                    "return_id": return_record.get(
                        "return_id"
                    ),
                    "return_status": return_status,
                    "reason": (
                        "A return record exists, but the "
                        "available data does not show the "
                        "returned item as RECEIVED or COMPLETED."
                    ),
                    "checks": {
                        "order_verified": True,
                        "payment_successful": True,
                        "return_record_exists": True,
                        "return_receipt_checked": True,
                        "return_received": False,
                    },
                    "policy_evidence": (
                        policy_evidence
                    ),
                    "policy_sources": [
                        "amazon_policy.json",
                        "casepilot_policy.json",
                    ],
                }

        # =========================================================
        # 15. EXISTING NOT_INITIATED REFUND
        # =========================================================

        if not_initiated_refund:

            existing_refund_amount = _safe_amount(
                not_initiated_refund.get(
                    "refund_amount"
                )
            )

            return {
                "success": True,
                "eligible": True,
                "order_id": order_id,
                "amount": order_amount,
                "refund_id": (
                    not_initiated_refund.get(
                        "refund_id"
                    )
                ),
                "refund_status": "NOT_INITIATED",
                "existing_refund_amount": (
                    existing_refund_amount
                ),
                "reason": (
                    "The order passed the available refund "
                    "eligibility checks and has an existing "
                    "NOT_INITIATED refund record."
                ),
                "checks": {
                    "order_verified": True,
                    "payment_successful": True,
                    "refund_already_exists": True,
                    "completed_refund": False,
                    "processing_refund": False,
                    "return_receipt_checked": (
                        return_receipt_required
                    ),
                    "return_received": (
                        return_received
                        if return_receipt_required
                        else None
                    ),
                },
                "policy_checks_required": (
                    refund_verification_checks
                ),
                "policy_evidence": (
                    policy_evidence
                ),
                "policy_sources": [
                    "amazon_policy.json",
                    "casepilot_policy.json",
                ],
                "next_action": "CREATE_REFUND",
            }

        # =========================================================
        # 16. RETURNLESS RESOLUTION
        # =========================================================

        if (
            product_returnless_eligible is True
            and not return_record
        ):

            returnless_policy = amazon_policy.get(
                "returnless_resolution",
                {},
            )

            returnless_guidance = ""

            if isinstance(
                returnless_policy,
                dict,
            ):
                returnless_guidance = str(
                    returnless_policy.get(
                        "guidance",
                        ""
                    )
                    or ""
                ).strip()

            return {
                "success": True,
                "eligible": False,
                "order_id": order_id,
                "amount": order_amount,
                "reason": (
                    "The product is marked as potentially "
                    "eligible for returnless resolution, "
                    "but the supplied policy requires "
                    "specific SKU/product/case eligibility "
                    "to be checked before assuming a refund."
                ),
                "returnless_resolution_possible": True,
                "returnless_policy_guidance": (
                    returnless_guidance
                ),
                "checks": {
                    "order_verified": True,
                    "payment_successful": True,
                    "product_verified": True,
                    "returnless_metadata": True,
                    "case_specific_returnless_check": False,
                },
                "policy_evidence": (
                    policy_evidence
                ),
                "policy_sources": [
                    "amazon_policy.json",
                    "casepilot_policy.json",
                ],
            }

        # =========================================================
        # 17. POLICY-SUPPORTED REFUND CANDIDATE
        # =========================================================

        return {
            "success": True,
            "eligible": True,
            "order_id": order_id,
            "amount": order_amount,
            "refund_status": "NOT_INITIATED",
            "reason": (
                "The order, successful payment, product "
                "eligibility data, existing refund state, "
                "and applicable return evidence passed the "
                "available refund checks."
            ),
            "checks": {
                "order_verified": True,
                "payment_successful": True,
                "product_verified": True,
                "completed_refund": False,
                "processing_refund": False,
                "return_receipt_checked": (
                    return_receipt_required
                ),
                "return_received": (
                    return_received
                    if return_receipt_required
                    else None
                ),
            },
            "policy_checks_required": (
                refund_verification_checks
            ),
            "policy_evidence": (
                policy_evidence
            ),
            "policy_sources": [
                "amazon_policy.json",
                "casepilot_policy.json",
            ],
            "next_action": "CREATE_REFUND",
        }

    except S3PolicyError as exc:

        return {
            "success": False,
            "eligible": False,
            "error_code": "S3_POLICY_ERROR",
            "order_id": order_id,
            "reason": (
                "The applicable CasePilot policy could "
                "not be loaded from S3."
            ),
            "details": str(exc),
        }

    except DatabaseError as exc:

        return {
            "success": False,
            "eligible": False,
            "error_code": "DATABASE_ERROR",
            "order_id": order_id,
            "reason": str(exc),
        }

    except (
        ValueError,
        TypeError,
    ) as exc:

        return {
            "success": False,
            "eligible": False,
            "error_code": "INVALID_ELIGIBILITY_DATA",
            "order_id": order_id,
            "reason": str(exc),
        }

    except Exception as exc:

        return {
            "success": False,
            "eligible": False,
            "error_code": "ELIGIBILITY_CHECK_FAILED",
            "order_id": order_id,
            "reason": (
                "An unexpected error occurred while "
                f"checking refund eligibility: {exc}"
            ),
        }