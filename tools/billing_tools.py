"""
Billing Specialist Tools: Deterministic business rules for refunds and invoice verifications.
"""

from __future__ import annotations

from typing import Any, Dict


def check_refund_eligibility(
    transaction_id: str,
    days_since_purchase: int = 1,
    amount: float = 0.0,
    reason: str = "unfulfilled_service",
) -> Dict[str, Any]:
    """
    Evaluate refund request against enterprise financial policies.
    Rules:
    - 0 to 30 days: Full refund eligible (100%).
    - 31 to 60 days: Eligible for prorated store credit (85%).
    - > 60 days: Policy expired; requires managerial manual override.
    - Amount > $500: Compliance flag for secondary fraud verification.
    """
    days = max(0, int(days_since_purchase))
    txn = transaction_id.strip() if transaction_id else "TXN-UNKNOWN"

    result: Dict[str, Any] = {
        "transaction_id": txn,
        "days_since_purchase": days,
        "eligible": False,
        "refund_type": "NONE",
        "refund_percentage": 0,
        "policy_code": "REF-POL-2026",
        "requires_manager_approval": False,
        "explanation": "",
    }

    if amount > 500.0:
        result["requires_manager_approval"] = True

    if days <= 30:
        result["eligible"] = True
        result["refund_type"] = "FULL_REFUND_TO_PAYMENT_METHOD"
        result["refund_percentage"] = 100
        result["explanation"] = (
            f"Transaction {txn} is within the 30-day money-back guarantee window ({days} days elapsed). "
            f"Eligible for 100% full refund to original payment source."
        )
    elif days <= 60:
        result["eligible"] = True
        result["refund_type"] = "PRORATED_STORE_CREDIT"
        result["refund_percentage"] = 85
        result["explanation"] = (
            f"Transaction {txn} is between 31 and 60 days ({days} days elapsed). "
            f"Eligible for 85% store credit under Extended Grace Terms."
        )
    else:
        result["eligible"] = False
        result["refund_type"] = "EXPIRED"
        result["refund_percentage"] = 0
        result["requires_manager_approval"] = True
        result["explanation"] = (
            f"Transaction {txn} is beyond the 60-day standard refund window ({days} days elapsed). "
            f"Direct automated refund is not permitted."
        )

    return result


def verify_invoice_and_payment_status(
    order_id: str, transaction_id: str = ""
) -> Dict[str, Any]:
    """
    Look up payment settlement status and order confirmation state.
    """
    ord_id = order_id.strip() if order_id else "ORD-UNKNOWN"
    txn_id = transaction_id.strip() if transaction_id else f"TXN-{abs(hash(ord_id)) % 100000}"

    return {
        "order_id": ord_id,
        "transaction_id": txn_id,
        "payment_status": "CAPTURED",
        "settlement_currency": "USD",
        "order_status": "PENDING_CONFIRMATION_SYNC",
        "gateway_response": "PAYMENT_SUCCESS_WEBHOOK_DELAYED",
        "recommended_action": (
            "Payment deduction has been verified at the gateway level. "
            "Order confirmation was delayed by an asynchronous event bus lag. "
            "Manual or automated confirmation push will link payment to order within 1 hour."
        ),
    }
