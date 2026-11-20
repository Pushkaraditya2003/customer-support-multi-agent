"""
Unit tests for individual specialized agents.
"""

import pytest
from memory.blackboard import Blackboard
from memory.event_log import EventLog
from agents.classifier_agent import ClassifierAgent
from agents.billing_specialist import BillingSpecialist
from agents.technical_specialist import TechnicalSpecialist
from agents.account_specialist import AccountSpecialist
from agents.escalation_router import EscalationRouter
from agents.reviewer_agent import ReviewerAgent


def test_classifier_agent():
    agent = ClassifierAgent()
    bb = Blackboard("T-1", "C-1", "I need a refund for my payment of $50 on order ORD-9988.")
    log = EventLog()

    out = agent.process(bb, log)
    assert out["category"] == "billing"
    assert out["confidence"] >= 0.70
    assert bb.get_section("classification")["category"] == "billing"
    assert len(log) == 1


def test_billing_specialist():
    agent = BillingSpecialist()
    bb = Blackboard("T-2", "C-2", "Refund request.")
    bb.update_section("classification", {"category": "billing", "entities": {"order_ids": ["ORD-111"]}})
    log = EventLog()

    out = agent.process(bb, log)
    assert out["specialist_name"] == "BillingSpecialist"
    assert out["is_resolved"] is True
    assert bb.get_value("draft_response") is not None


def test_technical_specialist_with_error_code():
    agent = TechnicalSpecialist()
    bb = Blackboard("T-3", "C-3", "Getting error ERR-1001 gateway timeout.")
    bb.update_section("classification", {"category": "technical", "entities": {"error_codes": ["ERR-1001"]}})
    log = EventLog()

    out = agent.process(bb, log)
    assert out["specialist_name"] == "TechnicalSpecialist"
    assert out["is_resolved"] is True
    assert "[error_codes.txt#ERR-1001]" in out["evidence"]


def test_technical_specialist_insufficient_evidence():
    agent = TechnicalSpecialist()
    bb = Blackboard("T-4", "C-4", "How do I configure supersonic quantum propulsion?")
    bb.update_section("classification", {"category": "technical", "entities": {}})
    log = EventLog()

    out = agent.process(bb, log)
    assert out["is_resolved"] is False
    assert out["needs_escalation"] is True


def test_account_specialist():
    agent = AccountSpecialist()
    bb = Blackboard("T-5", "C-5", "I forgot my password for account ACC-8899.")
    bb.update_section("classification", {"category": "account", "entities": {"account_ids": ["ACC-8899"]}})
    log = EventLog()

    out = agent.process(bb, log)
    assert out["specialist_name"] == "AccountSpecialist"
    assert out["is_resolved"] is True
    assert "RST-" in out["metadata"]["reset_token"]


def test_escalation_router():
    agent = EscalationRouter()
    bb = Blackboard("T-6", "C-6", "Unknown query.")
    bb.update_section("classification", {"category": "other", "confidence": 0.40})
    bb.update_section("specialist_output", {"is_resolved": False, "evidence": []})
    log = EventLog()

    out = agent.process(bb, log, trigger_reason="Category other")
    assert out["is_escalated"] is True
    assert bb.status == "ESCALATED"
    assert "HUMAN ESCALATION BRIEFING" in out["handoff_note"]


def test_reviewer_agent():
    agent = ReviewerAgent()
    bb = Blackboard("T-7", "C-7", "Test ticket.")
    bb.update_section("classification", {"category": "billing"})
    bb.set_value(
        "draft_response",
        "Hello, thank you for reaching out to Enterprise Support. "
        "We have processed your refund request and your bank will reflect the funds in 3-5 days. "
        "Please let us know if you need any additional help.",
    )
    log = EventLog()

    out = agent.process(bb, log)
    assert out["approved"] is True
    assert bb.get_value("final_response") is not None
