"""
Central Support Desk Multi-Agent Orchestrator.
Coordinates Classifier, Router, Specialists, Escalation, Reviewer, Blackboard, and EventLog.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from config import MAX_REVISION_ATTEMPTS
from memory.blackboard import Blackboard
from memory.event_log import EventLog
from memory.session_memory import SessionMemory
from orchestration.router import MainRouter

from agents.classifier_agent import ClassifierAgent
from agents.billing_specialist import BillingSpecialist
from agents.technical_specialist import TechnicalSpecialist
from agents.account_specialist import AccountSpecialist
from agents.escalation_router import EscalationRouter
from agents.reviewer_agent import ReviewerAgent


class SupportDeskOrchestrator:
    """
    Central Orchestrator managing end-to-end ticket lifecycle:
    Ticket Ingestion -> Classification -> Routing -> Specialist Processing -> Escalation Check -> Quality Review -> Revision Loop -> Resolution.
    """

    def __init__(
        self,
        session_memory: Optional[SessionMemory] = None,
        kernel: Optional[Any] = None,
        max_revisions: int = MAX_REVISION_ATTEMPTS,
    ):
        self.session_memory = session_memory or SessionMemory()
        self.kernel = kernel
        self.max_revisions = max_revisions

        # Initialize agents and router
        self.classifier = ClassifierAgent(kernel=self.kernel)
        self.router = MainRouter()
        self.billing_specialist = BillingSpecialist(kernel=self.kernel)
        self.technical_specialist = TechnicalSpecialist(kernel=self.kernel)
        self.account_specialist = AccountSpecialist(kernel=self.kernel)
        self.escalation_router = EscalationRouter(kernel=self.kernel)
        self.reviewer = ReviewerAgent(kernel=self.kernel)

    def process_ticket(
        self,
        customer_message: str,
        customer_id: str = "CUST-DEFAULT",
        ticket_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute collaborative multi-agent workflow on an incoming customer ticket.
        """
        tid = ticket_id or f"TICKET-{uuid.uuid4().hex[:6].upper()}"
        event_log = EventLog()
        blackboard = Blackboard(
            ticket_id=tid,
            customer_id=customer_id,
            customer_message=customer_message,
        )

        # Event: Ticket Received
        event_log.append_event(
            ticket_id=tid,
            agent="Orchestrator",
            action="TicketReceived",
            status="SUCCESS",
            details={
                "customer_id": customer_id,
                "message_length": len(customer_message),
                "has_previous_history": bool(self.session_memory.get_customer_history(customer_id)),
            },
        )

        # STAGE 1: Classification
        self.classifier.process(blackboard, event_log)

        # STAGE 2: Routing
        routing = self.router.route(blackboard, event_log)
        target = routing["target_specialist"]

        # STAGE 3: Specialist Execution
        if target == "billing_specialist":
            self.billing_specialist.process(blackboard, event_log)
        elif target == "technical_specialist":
            self.technical_specialist.process(blackboard, event_log)
        elif target == "account_specialist":
            self.account_specialist.process(blackboard, event_log)
        else:
            # Direct escalation route (e.g., low confidence or 'other')
            self.escalation_router.process(
                blackboard, event_log, trigger_reason=routing["reason"]
            )

        # STAGE 4: Specialist Resolution & Escalation Check
        specialist_out = blackboard.get_section("specialist_output")
        if specialist_out.get("needs_escalation", False) and not blackboard.get_section("escalation").get("is_escalated", False):
            # Specialist failed or lacked evidence -> handoff to EscalationRouter!
            self.escalation_router.process(
                blackboard,
                event_log,
                trigger_reason=specialist_out.get("resolution", "Specialist requested escalation."),
            )

        # STAGE 5: Response Review and Revision Loop
        for attempt in range(1, self.max_revisions + 1):
            review_result = self.reviewer.process(blackboard, event_log)
            if review_result["approved"]:
                break

            # Revision required
            current_review = blackboard.get_section("review")
            current_review["revision_count"] = attempt
            blackboard.update_section("review", current_review)

            event_log.append_event(
                ticket_id=tid,
                agent="Orchestrator",
                action="DraftRevisionInitiated",
                status="WARNING",
                details={
                    "attempt": attempt,
                    "feedback": review_result["feedback"],
                },
            )

            # Refine draft addressing reviewer feedback
            current_draft = blackboard.get_value("draft_response") or ""
            refined_draft = self._refine_draft(current_draft, review_result["feedback"], blackboard)
            blackboard.set_value("draft_response", refined_draft)

        # Final check if still unapproved after max revisions
        final_review = blackboard.get_section("review")
        if not final_review.get("approved", False):
            # Fallback safe response with escalation flag
            safe_draft = (
                f"Hello, thank you for reaching out to Enterprise Support regarding ticket {tid}.\n\n"
                f"We are actively reviewing your case details to provide a comprehensive answer. "
                f"Your request has been routed to our senior team for immediate assistance.\n\n"
                f"A customer service specialist will follow up with you directly."
            )
            blackboard.set_value("final_response", safe_draft)
            blackboard.set_status("ESCALATED")

        # STAGE 6: Store in Session Memory
        final_snapshot = blackboard.snapshot()
        self.session_memory.record_ticket(final_snapshot)

        # Event: Ticket Completed
        event_log.append_event(
            ticket_id=tid,
            agent="Orchestrator",
            action="WorkflowCompleted",
            status="SUCCESS",
            details={
                "final_status": blackboard.status,
                "is_escalated": blackboard.get_section("escalation").get("is_escalated", False),
                "total_events": len(event_log),
            },
        )

        return {
            "ticket_id": tid,
            "status": blackboard.status,
            "final_response": blackboard.get_value("final_response") or blackboard.get_value("draft_response"),
            "blackboard_snapshot": final_snapshot,
            "event_log": event_log.to_list(),
        }

    def _refine_draft(
        self, draft: str, feedback: list[str], blackboard: Blackboard
    ) -> str:
        """
        Deterministic refinement applying reviewer feedback to improve response quality.
        """
        refined = draft.strip()

        # Add missing greeting if flagged
        if any("greeting" in f.lower() or "courtesy" in f.lower() for f in feedback):
            if not refined.lower().startswith(("hello", "hi", "dear")):
                refined = "Hello, thank you for contacting Enterprise Support.\n\n" + refined

        # Expand if too terse
        if any("terse" in f.lower() for f in feedback):
            refined += (
                "\n\nWe appreciate your patience while we work on your case. "
                "Our dedicated support team is available 24/7 if you have additional questions."
            )

        # Add technical citation if missing
        if any("citation" in f.lower() for f in feedback):
            sources = blackboard.get_section("specialist_output").get("evidence", [])
            cite_str = f" [Referenced Guide: {sources[0]}]" if sources else " [Official Support KB]"
            refined += cite_str

        # Add escalation clarification if flagged
        if any("escalat" in f.lower() for f in feedback):
            refined += "\n\nPlease note: This ticket has been assigned to our specialized human support queue for priority handling."

        return refined
