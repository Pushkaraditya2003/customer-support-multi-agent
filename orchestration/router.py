"""
Main Router: Implements Router-to-Specialists dispatch logic.
Routes tickets based on category, confidence thresholds, and specialist capabilities.
"""

from __future__ import annotations

from typing import Any, Dict
from config import CONFIDENCE_THRESHOLD
from memory.blackboard import Blackboard
from memory.event_log import EventLog


class MainRouter:
    """
    Central Router in the Router-to-Specialists architecture.
    Directs tickets to Billing, Technical, or Account Specialists,
    or redirects to Escalation Router if confidence is low or category is 'other'.
    """

    def __init__(self, confidence_threshold: float = CONFIDENCE_THRESHOLD):
        self.confidence_threshold = confidence_threshold

    def route(self, blackboard: Blackboard, event_log: EventLog) -> Dict[str, Any]:
        ticket_id = blackboard.ticket_id
        classification = blackboard.get_section("classification")
        category = classification.get("category", "other")
        confidence = classification.get("confidence", 0.0)

        # Rule 1: Low confidence check (< threshold)
        if confidence < self.confidence_threshold:
            routing_decision = {
                "target_specialist": "escalation_router",
                "route_type": "ESCALATION",
                "reason": f"Classification confidence ({confidence:.2f}) is below operational threshold ({self.confidence_threshold:.2f}).",
            }
        # Rule 2: Unmatched / 'other' category check
        elif category == "other":
            routing_decision = {
                "target_specialist": "escalation_router",
                "route_type": "ESCALATION",
                "reason": "Ticket belongs to 'other' (unsupported domain); requires human manual review.",
            }
        # Rule 3: Direct Specialist routing
        elif category == "billing":
            routing_decision = {
                "target_specialist": "billing_specialist",
                "route_type": "SPECIALIST",
                "reason": "Categorized as Billing with sufficient confidence.",
            }
        elif category == "technical":
            routing_decision = {
                "target_specialist": "technical_specialist",
                "route_type": "SPECIALIST",
                "reason": "Categorized as Technical with sufficient confidence.",
            }
        elif category == "account":
            routing_decision = {
                "target_specialist": "account_specialist",
                "route_type": "SPECIALIST",
                "reason": "Categorized as Account with sufficient confidence.",
            }
        else:
            routing_decision = {
                "target_specialist": "escalation_router",
                "route_type": "ESCALATION",
                "reason": f"Unknown category '{category}'; rerouting to human escalation.",
            }

        # Update Blackboard
        blackboard.update_section("routing", routing_decision)
        blackboard.set_status("ROUTED")

        # Record in Event Log
        event_log.append_event(
            ticket_id=ticket_id,
            agent="MainRouter",
            action="RoutingDecisionMade",
            status="SUCCESS",
            details=routing_decision,
        )

        return routing_decision
