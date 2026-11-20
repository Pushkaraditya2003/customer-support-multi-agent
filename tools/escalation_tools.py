"""
Escalation Router Tools: Criteria evaluation and human tier handoff note generation.
"""

from __future__ import annotations

from typing import Any, Dict


def evaluate_escalation_criteria(
    category: str,
    confidence: float,
    is_resolved: bool,
    sufficient_evidence: bool,
    customer_urgency: str = "NORMAL",
) -> Dict[str, Any]:
    """
    Deterministic rule engine to determine if ticket requires human intervention.
    """
    cat = category.strip().lower()
    needs_escalation = False
    reasons = []
    priority = "NORMAL"
    target_tier = "Tier 1 Support Team"

    # Condition 1: Low classification confidence (< 0.65)
    if confidence < 0.65:
        needs_escalation = True
        reasons.append(f"Classification confidence ({confidence:.2f}) is below confidence threshold (0.65).")
        priority = "MEDIUM"
        target_tier = "General Triage Specialists"

    # Condition 2: Category is 'other'
    if cat == "other":
        needs_escalation = True
        reasons.append("Ticket falls outside known standard categories ('other'); requires human review.")
        priority = "MEDIUM"
        target_tier = "General Operations Escalations"

    # Condition 3: Insufficient RAG / knowledge-base evidence
    if not sufficient_evidence:
        needs_escalation = True
        reasons.append("Specialist identified insufficient knowledge base evidence to answer authoritatively.")
        priority = "HIGH"
        target_tier = "Tier 2 Technical Support Engineering"

    # Condition 4: Specialist was unable to resolve
    if not is_resolved and not reasons:
        needs_escalation = True
        reasons.append("Specialist could not achieve automated resolution under standard policies.")
        priority = "HIGH"
        target_tier = f"Tier 2 {cat.title()} Escalation Desk"

    # Condition 5: Critical/Urgent priority override
    if customer_urgency.upper() in ["URGENT", "CRITICAL", "COMPROMISED", "EMERGENCY"]:
        priority = "URGENT"
        if cat == "account":
            target_tier = "Trust & Safety / Account Security Incident Team"

    return {
        "needs_escalation": needs_escalation,
        "escalation_reasons": reasons,
        "priority": priority,
        "target_tier": target_tier,
    }


def generate_escalation_handoff_note(
    ticket_id: str,
    reason: str,
    priority: str,
    target_tier: str,
    specialist_findings: str,
) -> str:
    """
    Generate an auditable handoff note for human support staff.
    """
    return (
        f"=== HUMAN ESCALATION BRIEFING ===\n"
        f"Ticket ID: {ticket_id}\n"
        f"Assigned Queue: {target_tier}\n"
        f"Priority Level: {priority}\n"
        f"Primary Escalation Reason: {reason}\n"
        f"Automated Specialist Diagnostics:\n{specialist_findings}\n"
        f"Action Required: Human agent manual intervention and direct customer follow-up.\n"
        f"================================="
    )
