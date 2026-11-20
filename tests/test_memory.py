"""
Unit tests for Blackboard, append-only Event Log, and Session Memory.
"""

import pytest
from memory.blackboard import Blackboard
from memory.event_log import EventLog
from memory.session_memory import SessionMemory


def test_blackboard_state_and_snapshot():
    bb = Blackboard(ticket_id="TICKET-01", customer_id="CUST-10", customer_message="Hello, I need help.")
    assert bb.ticket_id == "TICKET-01"
    assert bb.status == "RECEIVED"

    # Mutate section
    bb.update_section("classification", {"category": "billing", "confidence": 0.88})
    assert bb.get_section("classification")["category"] == "billing"

    # Verify snapshot isolation (modifying snapshot shouldn't modify internal state)
    snap = bb.snapshot()
    snap["classification"]["category"] = "technical"
    assert bb.get_section("classification")["category"] == "billing"


def test_event_log_append_only():
    log = EventLog()
    assert len(log) == 0

    e1 = log.append_event(ticket_id="TICKET-01", agent="Classifier", action="ClassificationCompleted")
    assert e1.event_id == "EVT-0001"
    assert len(log) == 1

    e2 = log.append_event(ticket_id="TICKET-01", agent="Router", action="RoutingDecision")
    assert e2.event_id == "EVT-0002"
    assert len(log) == 2

    # Events list is immutable copy
    events = log.get_events()
    assert len(events) == 2


def test_session_memory_retention_and_followup():
    sm = SessionMemory()
    snapshot = {
        "ticket_id": "TICKET-101",
        "customer_id": "CUST-A",
        "created_at": "2026-11-20T10:00:00Z",
        "status": "RESOLVED",
        "classification": {"category": "billing"},
        "routing": {"target_specialist": "billing_specialist"},
        "final_response": "Your payment has been processed and order confirmed.",
        "escalation": {"is_escalated": False},
    }
    sm.record_ticket(snapshot)

    # Retrieve history
    history = sm.get_customer_history("CUST-A")
    assert len(history) == 1
    assert history[0]["ticket_id"] == "TICKET-101"
    assert history[0]["category"] == "billing"

    # Context formatting for LLM/prompt
    ctx = sm.build_history_context("CUST-A")
    assert "TICKET-101" in ctx
    assert "billing" in ctx
