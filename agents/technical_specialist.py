"""
Agent 3: Technical Specialist
Handles error codes, troubleshooting, and how-to inquiries.
Uses RAG over local support knowledge base to strictly ground resolutions.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from semantic_kernel.functions import kernel_function

from tools.technical_tools import query_technical_knowledge_base, diagnose_error_code
from memory.blackboard import Blackboard
from memory.event_log import EventLog


class TechnicalPlugin:
    """Semantic Kernel plugin for technical knowledge retrieval and diagnostics."""

    @kernel_function(
        name="search_knowledge_base",
        description="Query local technical documentation for troubleshooting guides and solutions.",
    )
    def search_knowledge_base(self, query: str) -> str:
        res = query_technical_knowledge_base(query)
        return json.dumps(res)

    @kernel_function(
        name="lookup_error",
        description="Diagnose standard error code and retrieve authorized remediation procedure.",
    )
    def lookup_error(self, error_code: str) -> str:
        res = diagnose_error_code(error_code)
        return json.dumps(res)


class TechnicalSpecialist:
    """
    Technical Specialist Agent that leverages RAG over the local knowledge base.
    If knowledge base evidence is insufficient, flags needs_escalation=True without hallucinating.
    """

    def __init__(self, kernel: Optional[Any] = None):
        self.kernel = kernel
        self.plugin = TechnicalPlugin()
        if self.kernel:
            self.kernel.add_plugin(self.plugin, plugin_name="technical_tools")

    def process(self, blackboard: Blackboard, event_log: EventLog) -> Dict[str, Any]:
        ticket_id = blackboard.ticket_id
        message = blackboard.get_value("customer_message")
        entities = blackboard.get_section("classification").get("entities", {})

        error_codes = entities.get("error_codes", [])
        evidence_sources = []
        is_resolved = False
        needs_escalation = False
        resolution_notes = ""
        draft_response = ""

        # Step 1: Check for explicit error code
        if error_codes:
            diag = diagnose_error_code(error_codes[0])
            if diag["found"]:
                evidence_sources.append(diag["source"])
                resolution_notes = f"Error Diagnosis for {diag['error_code']}: {diag['root_cause']}. Remediation: {diag['remediation']}"
                draft_response = (
                    f"Hello, thank you for contacting Enterprise Technical Support.\n\n"
                    f"We have identified the root cause for {diag['error_code']} ({diag['title']}). "
                    f"This issue occurs because: {diag['root_cause']}.\n\n"
                    f"Recommended Resolution Steps:\n"
                    f"1. {diag['remediation']}\n"
                    f"2. Reference Documentation: {diag['source']}.\n\n"
                    f"If the problem persists after following these steps, please let us know so our team can investigate your environment."
                )
                is_resolved = True

        # Step 2: RAG semantic vector search over knowledge base
        if not is_resolved:
            rag_result = query_technical_knowledge_base(message)
            if rag_result["sufficient_evidence"]:
                evidence_sources.extend(rag_result["sources"])
                resolution_notes = f"Retrieved {len(rag_result['sources'])} supporting documentation passages."
                draft_response = (
                    f"Hello, thank you for reaching out to Enterprise Technical Support.\n\n"
                    f"Based on our official technical support documentation {evidence_sources[0] if evidence_sources else ''}, "
                    f"here is the recommended troubleshooting procedure for your issue:\n\n"
                    f"{rag_result['context'][:350]}...\n\n"
                    f"Please apply these steps and verify if the issue resolves. Sources cited: {', '.join(evidence_sources)}."
                )
                is_resolved = True
            else:
                # INSUFFICIENT EVIDENCE -> Escalate to human engineers!
                needs_escalation = True
                is_resolved = False
                resolution_notes = "RAG search returned insufficient evidence in local knowledge base."
                draft_response = (
                    f"Hello, thank you for contacting Enterprise Technical Support.\n\n"
                    f"We have analyzed your technical inquiry. Because this specific behavior is not covered "
                    f"under our standard automated knowledge base documentation, we have escalated your ticket "
                    f"to our Tier 2 Technical Engineering team for manual log inspection.\n\n"
                    f"A senior technical engineer will review your system diagnostics and follow up with you shortly."
                )

        specialist_data = {
            "specialist_name": "TechnicalSpecialist",
            "resolution": resolution_notes,
            "evidence": evidence_sources,
            "is_resolved": is_resolved,
            "needs_escalation": needs_escalation,
            "metadata": {
                "error_codes_identified": error_codes,
                "sources_cited": evidence_sources,
            },
        }

        # Update Blackboard
        blackboard.update_section("specialist_output", specialist_data)
        blackboard.set_value("draft_response", draft_response)
        blackboard.set_status("SPECIALIST_PROCESSED")

        # Record in Event Log
        event_log.append_event(
            ticket_id=ticket_id,
            agent="TechnicalSpecialist",
            action="RAGKnowledgeRetrieved" if is_resolved else "InsufficientEvidenceIdentified",
            status="SUCCESS" if is_resolved else "ESCALATED",
            details={
                "is_resolved": is_resolved,
                "sources": evidence_sources,
                "needs_escalation": needs_escalation,
            },
        )

        return specialist_data
