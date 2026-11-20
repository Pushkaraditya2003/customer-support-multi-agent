"""
Agent 6: Reviewer Agent
Checks tone, completeness, and compliance of drafted customer responses.
Approves or rejects responses with revision instructions up to MAX_REVISION_ATTEMPTS.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from semantic_kernel.functions import kernel_function

from tools.reviewer_tools import validate_response_quality, check_compliance_and_safety
from memory.blackboard import Blackboard
from memory.event_log import EventLog


class ReviewerPlugin:
    """Semantic Kernel plugin for response validation and quality control."""

    @kernel_function(
        name="validate_quality",
        description="Check customer response tone, courtesy, clarity, and completeness.",
    )
    def validate_quality(self, draft_text: str, category: str, is_escalated: bool = False) -> str:
        res = validate_response_quality(draft_text, category, is_escalated)
        return json.dumps(res)

    @kernel_function(
        name="check_compliance",
        description="Verify response complies with safety policies and avoids unauthorized promises.",
    )
    def check_compliance(self, draft_text: str) -> str:
        res = check_compliance_and_safety(draft_text)
        return json.dumps(res)


class ReviewerAgent:
    """
    Reviewer Agent that conducts rigorous quality assurance on all proposed customer responses.
    Can reject unsatisfactory drafts, triggering automated refinement.
    """

    def __init__(self, kernel: Optional[Any] = None):
        self.kernel = kernel
        self.plugin = ReviewerPlugin()
        if self.kernel:
            self.kernel.add_plugin(self.plugin, plugin_name="reviewer_tools")

    def process(self, blackboard: Blackboard, event_log: EventLog) -> Dict[str, Any]:
        ticket_id = blackboard.ticket_id
        draft = blackboard.get_value("draft_response") or ""
        classification = blackboard.get_section("classification")
        category = classification.get("category", "other")
        escalation = blackboard.get_section("escalation")
        is_escalated = escalation.get("is_escalated", False)
        specialist_output = blackboard.get_section("specialist_output")
        sources = specialist_output.get("evidence", [])

        current_review = blackboard.get_section("review")
        rev_count = current_review.get("revision_count", 0)

        # Run quality inspection
        qual = validate_response_quality(
            draft_text=draft,
            category=category,
            is_escalated=is_escalated,
            sources_cited=sources,
        )
        comp = check_compliance_and_safety(draft)

        feedback = list(qual["feedback"])
        if not comp["compliant"]:
            feedback.extend(comp["flags"])

        approved = qual["approved"] and comp["compliant"]

        review_data = {
            "approved": approved,
            "tone_score": qual["tone_score"],
            "completeness_score": qual["completeness_score"],
            "feedback": feedback,
            "revision_count": rev_count,
        }

        # Update Blackboard
        blackboard.update_section("review", review_data)
        if approved:
            blackboard.set_value("final_response", draft)
            blackboard.set_status("RESOLVED" if not is_escalated else "ESCALATED")
        else:
            blackboard.set_status("REVISION_REQUIRED")

        # Record in Event Log
        event_log.append_event(
            ticket_id=ticket_id,
            agent="ReviewerAgent",
            action="ResponseApproved" if approved else "ResponseRejected",
            status="SUCCESS" if approved else "REJECTED",
            details={
                "approved": approved,
                "tone_score": qual["tone_score"],
                "completeness_score": qual["completeness_score"],
                "feedback": feedback,
                "revision_count": rev_count,
            },
        )

        return review_data
