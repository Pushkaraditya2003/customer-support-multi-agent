"""
Unit tests for all deterministic Python agent tools.
"""

import pytest
from tools.classifier_tools import (
    extract_ticket_entities,
    rule_based_category_hint,
    calculate_classification_confidence,
)
from tools.billing_tools import (
    check_refund_eligibility,
    verify_invoice_and_payment_status,
)
from tools.technical_tools import (
    diagnose_error_code,
    query_technical_knowledge_base,
)
from tools.account_tools import (
    verify_account_security_status,
    initiate_secure_password_reset,
)
from tools.escalation_tools import (
    evaluate_escalation_criteria,
    generate_escalation_handoff_note,
)
from tools.reviewer_tools import (
    validate_response_quality,
    check_compliance_and_safety,
)


def test_classifier_extract_entities():
    sample = "I got charged $49.99 on order ORD-88129 with transaction TXN-10023. Account ACC-5511."
    entities = extract_ticket_entities(sample)
    assert "88129" in entities["order_ids"] or "ORD-88129" in entities["order_ids"]
    assert "10023" in entities["transaction_ids"]
    assert "5511" in entities["account_ids"]
    assert any("49.99" in m for m in entities["monetary_amounts"])


def test_classifier_rule_hint_and_confidence():
    billing_txt = "My payment was deducted twice for this invoice refund."
    cat, conf = rule_based_category_hint(billing_txt)
    assert cat == "billing"
    assert conf >= 0.70

    other_txt = "The quick brown fox jumps over the lazy dog."
    cat_o, conf_o = rule_based_category_hint(other_txt)
    assert cat_o == "other"
    assert conf_o < 0.65


def test_billing_refund_eligibility():
    # <= 30 days -> 100% refund
    res30 = check_refund_eligibility("TXN-01", days_since_purchase=10, amount=50.0)
    assert res30["eligible"] is True
    assert res30["refund_percentage"] == 100
    assert res30["refund_type"] == "FULL_REFUND_TO_PAYMENT_METHOD"

    # 45 days -> 85% credit
    res45 = check_refund_eligibility("TXN-02", days_since_purchase=45, amount=50.0)
    assert res45["eligible"] is True
    assert res45["refund_percentage"] == 85

    # 90 days -> expired
    res90 = check_refund_eligibility("TXN-03", days_since_purchase=90, amount=50.0)
    assert res90["eligible"] is False
    assert res90["requires_manager_approval"] is True


def test_billing_invoice_status():
    inv = verify_invoice_and_payment_status("ORD-1234")
    assert inv["order_id"] == "ORD-1234"
    assert inv["payment_status"] == "CAPTURED"


def test_technical_diagnose_error():
    diag = diagnose_error_code("ERR-1001")
    assert diag["found"] is True
    assert "Timeout" in diag["title"]
    assert "error_codes.txt" in diag["source"]

    unknown = diagnose_error_code("ERR-9999")
    assert unknown["found"] is False


def test_account_security_status():
    sec_active = verify_account_security_status("ACC-1234", "user@test.com")
    assert sec_active["status"] == "ACTIVE"
    assert sec_active["is_locked"] is False

    sec_compromised = verify_account_security_status("ACC-1234-compromised")
    assert sec_compromised["status"] == "COMPROMISED"
    assert sec_compromised["risk_level"] == "CRITICAL"


def test_account_password_reset():
    reset = initiate_secure_password_reset("ACC-1234", "user@test.com")
    assert reset["reset_token_id"].startswith("RST-")
    assert reset["validity_minutes"] == 15


def test_escalation_criteria():
    # Low confidence escalates
    esc_conf = evaluate_escalation_criteria(category="technical", confidence=0.50, is_resolved=True, sufficient_evidence=True)
    assert esc_conf["needs_escalation"] is True

    # Category 'other' escalates
    esc_other = evaluate_escalation_criteria(category="other", confidence=0.90, is_resolved=True, sufficient_evidence=True)
    assert esc_other["needs_escalation"] is True

    # Insufficient evidence escalates
    esc_no_ev = evaluate_escalation_criteria(category="technical", confidence=0.90, is_resolved=True, sufficient_evidence=False)
    assert esc_no_ev["needs_escalation"] is True


def test_reviewer_quality_validation():
    # Too terse and missing greeting
    bad_draft = "Your order is confirmed."
    val_bad = validate_response_quality(bad_draft, category="billing")
    assert val_bad["approved"] is False
    assert len(val_bad["feedback"]) >= 2

    # Compliant professional response
    good_draft = (
        "Hello, thank you for contacting Enterprise Support. "
        "We have verified your transaction and pushed your order confirmation. "
        "Your confirmation email will arrive within an hour. Please let us know if you need anything else."
    )
    val_good = validate_response_quality(good_draft, category="billing")
    assert val_good["approved"] is True
    assert val_good["tone_score"] == 1.0


def test_reviewer_compliance():
    unsafe = "I promise 100% you will get money back immediately without review."
    comp = check_compliance_and_safety(unsafe)
    assert comp["compliant"] is False
