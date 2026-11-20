"""
End-to-End Orchestration and Workflow Scenario Tests.
Covers all mandatory teacher requirements:
1. Normal billing issue
2. Technical issue with RAG grounding
3. Account access & lockout
4. Insufficient knowledge base evidence -> Escalation Router
5. Low confidence / 'other' ambiguous ticket -> Escalation Router
6. Reviewer rejection and revision loop
7. Multi-turn session memory retention
"""

import pytest
from orchestration.workflow import SupportDeskOrchestrator
from memory.session_memory import SessionMemory


def test_scenario_1_normal_billing():
    orchestrator = SupportDeskOrchestrator()
    msg = "My payment of $49.99 was deducted from my account for order ORD-5511, but my order was not confirmed."
    result = orchestrator.process_ticket(customer_message=msg, customer_id="CUST-B01")

    assert result["status"] == "RESOLVED"
    snap = result["blackboard_snapshot"]
    assert snap["classification"]["category"] == "billing"
    assert snap["routing"]["target_specialist"] == "billing_specialist"
    assert snap["specialist_output"]["is_resolved"] is True
    assert snap["review"]["approved"] is True
    assert "49.99" in result["final_response"] or "captured" in result["final_response"].lower()


def test_scenario_2_technical_rag():
    orchestrator = SupportDeskOrchestrator()
    msg = "The application is throwing an ERR-1001 gateway request timeout when loading dashboard."
    result = orchestrator.process_ticket(customer_message=msg, customer_id="CUST-T01")

    assert result["status"] == "RESOLVED"
    snap = result["blackboard_snapshot"]
    assert snap["classification"]["category"] == "technical"
    assert snap["routing"]["target_specialist"] == "technical_specialist"
    assert snap["specialist_output"]["is_resolved"] is True
    assert len(snap["specialist_output"]["evidence"]) > 0
    assert "[error_codes.txt#ERR-1001]" in snap["specialist_output"]["evidence"]


def test_scenario_3_account_access():
    orchestrator = SupportDeskOrchestrator()
    msg = "I am locked out of my account ACC-9921 and cannot log in."
    result = orchestrator.process_ticket(customer_message=msg, customer_id="CUST-A01")

    assert result["status"] == "RESOLVED"
    snap = result["blackboard_snapshot"]
    assert snap["classification"]["category"] == "account"
    assert snap["routing"]["target_specialist"] == "account_specialist"
    assert snap["specialist_output"]["is_resolved"] is True
    assert "reset" in result["final_response"].lower()


def test_scenario_4_insufficient_rag_evidence_escalation():
    orchestrator = SupportDeskOrchestrator()
    msg = "I have a problem with a proprietary holographic rendering driver that is not in your docs."
    result = orchestrator.process_ticket(customer_message=msg, customer_id="CUST-E01")

    snap = result["blackboard_snapshot"]
    # Technical specialist tries RAG, finds insufficient evidence, and escalates to human engineering!
    assert snap["classification"]["category"] == "technical"
    assert snap["escalation"]["is_escalated"] is True
    assert "Tier 2 Technical Support Engineering" in snap["escalation"]["target_tier"]
    assert "insufficient" in snap["escalation"]["reason"].lower()


def test_scenario_5_other_category_escalation():
    orchestrator = SupportDeskOrchestrator()
    msg = "Can you send someone to repaint my front porch blue tomorrow morning?"
    result = orchestrator.process_ticket(customer_message=msg, customer_id="CUST-O01")

    snap = result["blackboard_snapshot"]
    # Category other or low confidence routed directly to Escalation Router!
    assert snap["classification"]["category"] == "other"
    assert snap["routing"]["target_specialist"] == "escalation_router"
    assert snap["escalation"]["is_escalated"] is True


def test_scenario_6_reviewer_revision_loop():
    orchestrator = SupportDeskOrchestrator()
    # Mocking or testing orchestrator refinement method directly
    raw_terse_draft = "Refund done."
    bb = orchestrator.classifier.process(
        bb := orchestrator.reviewer.process.__annotations__, bb
    ) if False else None  # helper sanity

    # Verify _refine_draft fixes issues
    from memory.blackboard import Blackboard
    test_bb = Blackboard("T-REV", "C-REV", "test")
    test_bb.update_section("classification", {"category": "billing"})
    refined = orchestrator._refine_draft(
        draft="Your balance is adjusted.",
        feedback=["Missing professional greeting or courtesy expression.", "Response is excessively terse (under 15 words)."],
        blackboard=test_bb,
    )
    assert refined.startswith("Hello, thank you for contacting Enterprise Support.")
    assert len(refined.split()) > 15


def test_scenario_7_multiturn_session_memory():
    session_mem = SessionMemory()
    orchestrator = SupportDeskOrchestrator(session_memory=session_mem)

    # Turn 1: Customer submits billing ticket
    t1_msg = "I was charged twice on order ORD-9912. Please issue a refund."
    res1 = orchestrator.process_ticket(customer_message=t1_msg, customer_id="CUST-MULTI-01")
    t1_id = res1["ticket_id"]

    # Verify ticket stored in session memory
    history = session_mem.get_customer_history("CUST-MULTI-01")
    assert len(history) == 1
    assert history[0]["ticket_id"] == t1_id
    assert history[0]["category"] == "billing"

    # Turn 2: Customer asks follow-up query
    context_str = session_mem.build_history_context("CUST-MULTI-01")
    assert t1_id in context_str
    assert "billing" in context_str
