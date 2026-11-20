"""
Classifier Tools: Entity extraction and classification confidence calculation.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


def extract_ticket_entities(text: str) -> Dict[str, Any]:
    """
    Extract structured identifiers and entities from raw customer ticket text.
    """
    entities: Dict[str, Any] = {
        "order_ids": [],
        "transaction_ids": [],
        "account_ids": [],
        "error_codes": [],
        "monetary_amounts": [],
        "emails": [],
        "urgency_keywords": [],
    }

    # Order IDs: e.g. ORD-9912, Order #98765, or Order 12345 (avoid matching "order was", "order is")
    order_matches = []
    for m in re.finditer(r"\b(ORD-[A-Za-z0-9\-]+)\b|\border\s*#\s*([A-Za-z0-9\-]+)\b|\border\s+([0-9][A-Za-z0-9\-]*)\b", text, re.IGNORECASE):
        val = m.group(1) or m.group(2) or m.group(3)
        if val and val.lower() not in ["was", "is", "not", "number", "id", "details", "confirmation"]:
            order_matches.append(val)
    entities["order_ids"] = list(set(order_matches))

    # Transaction IDs (e.g., TXN-10029, TXN-5544)
    txn_matches = re.findall(r"\b(?:TXN-|tx_)([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    entities["transaction_ids"] = list(set(txn_matches))

    # Account IDs (e.g., ACC-4421, user_991)
    acc_matches = re.findall(r"\b(?:ACC-|user_)([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    entities["account_ids"] = list(set(acc_matches))

    # Error codes (e.g., ERR-1001, Error 500)
    err_matches = re.findall(r"\b(ERR-\d{4}|HTTP\s*\d{3}|error\s*\d{3})\b", text, re.IGNORECASE)
    entities["error_codes"] = list(set(err_matches))

    # Monetary amounts (e.g., $49.99, 100 USD, 50 dollars)
    money_matches = re.findall(r"(\$\s*\d+(?:\.\d{2})?|\d+(?:\.\d{2})?\s*(?:USD|dollars?|EUR))", text, re.IGNORECASE)
    entities["monetary_amounts"] = list(set(money_matches))

    # Email addresses
    email_matches = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
    entities["emails"] = list(set(email_matches))

    # Urgency indicators
    urgency_terms = ["urgent", "immediately", "asap", "critical", "compromised", "emergency", "hacked"]
    low_text = text.lower()
    entities["urgency_keywords"] = [u for u in urgency_terms if u in low_text]

    return entities


def rule_based_category_hint(text: str) -> Tuple[str, float]:
    """
    Deterministic rule-based category heuristic and baseline confidence.
    Categories: billing, technical, account, other
    """
    low = text.lower()

    billing_keywords = [
        "refund", "charged", "payment", "invoice", "deducted", "subscription",
        "credit card", "price", "billing", "receipt", "purchase", "cost", "fee"
    ]
    technical_keywords = [
        "error", "bug", "crash", "timeout", "not working", "fails", "api",
        "gateway", "latency", "slow", "broken", "glitch", "err-", "technical",
        "driver", "feature", "software", "hardware", "system", "install",
        "configuration", "setup", "browser", "performance", "problem"
    ]
    account_keywords = [
        "login", "password", "2fa", "locked", "account", "unauthorized",
        "compromised", "hacked", "reset password", "credentials", "sign in", "auth"
    ]

    b_score = sum(1 for kw in billing_keywords if kw in low)
    t_score = sum(1 for kw in technical_keywords if kw in low)
    a_score = sum(1 for kw in account_keywords if kw in low)

    scores = [("billing", b_score), ("technical", t_score), ("account", a_score)]
    scores.sort(key=lambda x: x[1], reverse=True)

    best_cat, best_val = scores[0]
    total_matches = b_score + t_score + a_score

    if total_matches == 0:
        return "other", 0.40

    lead = best_val - scores[1][1]
    if lead >= 2:
        conf = 0.90
    elif lead == 1:
        conf = 0.78
    else:
        conf = 0.55  # Ambiguous conflict

    return best_cat, conf


def calculate_classification_confidence(
    text: str, category: str, extracted_entities: Dict[str, Any]
) -> float:
    """
    Compute structured classification confidence score between 0.0 and 1.0.
    """
    cat = category.strip().lower()
    if cat not in ["billing", "technical", "account", "other"]:
        return 0.20

    if cat == "other":
        return 0.45

    hint_cat, base_conf = rule_based_category_hint(text)

    # Entity booster: having category-specific entities raises confidence
    booster = 0.0
    if cat == "billing" and (extracted_entities.get("monetary_amounts") or extracted_entities.get("transaction_ids")):
        booster += 0.10
    elif cat == "technical" and extracted_entities.get("error_codes"):
        booster += 0.10
    elif cat == "account" and (extracted_entities.get("account_ids") or extracted_entities.get("emails")):
        booster += 0.10

    if cat == hint_cat:
        final_conf = min(0.98, base_conf + booster)
    else:
        final_conf = max(0.40, base_conf - 0.15 + booster)

    return round(final_conf, 2)
