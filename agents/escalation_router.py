"""
Agent 5: Escalation Router
Routes tickets to human queue when classification confidence is low,
when a specialist cannot resolve, or when category is 'other'.
Explains the reason for escalation.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from semantic_kernel.functions import kernel_function

from tools.escalation_tools import evaluate_escalation_criteria, generate_escalation_handoff_note
from memory.blackboard import Blackboard
from memory.event_log import EventLog


class EscalationPlugin:
    """Semantic Kernel plugin for escalation evaluation and queue routing."""

    @kernel_function(
        name="evaluate_escalation",
        description="Determine if a ticket requires human tier handoff based on confidence and resolution state.",
    )
    def evaluate_escalation(
        self,
        category: str,
        confidence: float,
        is_resolved: bool,
        sufficient_evidence: bool,
    ) -> str:
        res = evaluate_escalation_criteria(category, confidence, is_resolved, sufficient_evidence)
        return json.dumps(res)

    @kernel_function(
        name="format_handoff_note",
        description="Generate an internal briefing note for human support staff.",
    )
    def format_handoff_note(
        self, ticket_id: str, reason: str, priority: str, target_tier: str, findings: str
    ) -> str:
        return generate_escalation_handoff_note(ticket_id, reason, priority, target_tier, findings)


class EscalationRouter:
    """
    Escalation Router that handles low confidence, ambiguous queries, and unresolved specialist issues.
    Constructs an explicit escalation handoff and crafts transparent customer communication.
    """

    def __init__(self, kernel: Optional[Any] = None):
        self.kernel = kernel
        self.plugin = EscalationPlugin()
        if self.kernel:
            self.kernel.add_plugin(self.plugin, plugin_name="escalation_tools")

    def process(self, blackboard: Blackboard, event_log: EventLog, trigger_reason: str = "") -> Dict[str, Any]:
        ticket_id = blackboard.ticket_id
        classification = blackboard.get_section("classification")
        specialist_output = blackboard.get_section("specialist_output")

        category = classification.get("category") or "other"
        confidence = classification.get("confidence", 0.0)
        is_resolved = specialist_output.get("is_resolved", False)
        sufficient_evidence = bool(specialist_output.get("evidence", []))

        # Evaluate escalation rules
        eval_result = evaluate_escalation_criteria(
            category=category,
            confidence=confidence,
            is_resolved=is_resolved,
            sufficient_evidence=sufficient_evidence,
        )

        reasons = eval_result["escalation_reasons"]
        if trigger_reason and trigger_reason not in reasons:
            reasons.insert(0, trigger_reason)
        primary_reason = reasons[0] if reasons else "Manual escalation rule triggered."

        priority = eval_result["priority"]
        target_tier = eval_result["target_tier"]

        handoff_note = generate_escalation_handoff_note(
            ticket_id=ticket_id,
            reason=primary_reason,
            priority=priority,
            target_tier=target_tier,
            specialist_findings=str(specialist_output.get("resolution") or "No specialist resolution achieved."),
        )

        escalation_data = {
            "is_escalated": True,
            "reason": primary_reason,
            "all_reasons": reasons,
            "priority": priority,
            "target_tier": target_tier,
            "handoff_note": handoff_note,
        }

        # Compose empathetic customer explanation for the handoff
        escalation_customer_draft = (
            f"Hello, thank you for contacting Enterprise Support.\n\n"
            f"We have reviewed your request regarding your {category} inquiry. "
            f"To ensure you receive the highest quality assistance, your ticket has been prioritized "
            f"and routed to our {target_tier} (Priority: {priority}).\n\n"
            f"Reason for specialist transfer: {primary_reason}\n\n"
            f"A member of our team is reviewing your case history and will follow up with you directly."
        )

        # Update Blackboard
        blackboard.update_section("escalation", escalation_data)
        blackboard.set_value("draft_response", escalation_customer_draft)
        blackboard.set_status("ESCALATED")

        # Record in Event Log
        event_log.append_event(
            ticket_id=ticket_id,
            agent="EscalationRouter",
            action="TicketEscalatedToHuman",
            status="ESCALATED",
            details={
                "reason": primary_reason,
                "priority": priority,
                "target_tier": target_tier,
            },
        )

        return escalation_data
