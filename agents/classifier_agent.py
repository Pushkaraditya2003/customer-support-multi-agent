"""
Agent 1: Classifier Agent
Classifies tickets into billing, technical, account, or other.
Extracts entities and calculates classification confidence.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from semantic_kernel.functions import kernel_function

from tools.classifier_tools import (
    calculate_classification_confidence,
    extract_ticket_entities,
    rule_based_category_hint,
)
from memory.blackboard import Blackboard
from memory.event_log import EventLog


class ClassifierPlugin:
    """Semantic Kernel plugin for ticket classification tools."""

    @kernel_function(
        name="extract_entities",
        description="Extract structured entities like order ID, error code, account ID, and amounts from customer ticket.",
    )
    def extract_entities(self, ticket_text: str) -> str:
        entities = extract_ticket_entities(ticket_text)
        return json.dumps(entities)

    @kernel_function(
        name="classify_category",
        description="Classify the support ticket into billing, technical, account, or other, returning category and confidence.",
    )
    def classify_category(self, ticket_text: str) -> str:
        hint_cat, base_conf = rule_based_category_hint(ticket_text)
        entities = extract_ticket_entities(ticket_text)
        confidence = calculate_classification_confidence(ticket_text, hint_cat, entities)
        return json.dumps({
            "category": hint_cat,
            "confidence": confidence,
            "entities": entities,
        })


class ClassifierAgent:
    """
    Classifier Agent that analyzes customer ticket, classifies into one of 4 categories,
    computes confidence score, extracts entities, and updates Blackboard and EventLog.
    """

    def __init__(self, kernel: Optional[Any] = None):
        self.kernel = kernel
        self.plugin = ClassifierPlugin()
        if self.kernel:
            self.kernel.add_plugin(self.plugin, plugin_name="classifier_tools")

    def process(self, blackboard: Blackboard, event_log: EventLog) -> Dict[str, Any]:
        """
        Classify incoming customer message and update shared state.
        """
        message = blackboard.get_value("customer_message")
        ticket_id = blackboard.ticket_id

        # Deterministic extraction and classification
        entities = extract_ticket_entities(message)
        category, base_conf = rule_based_category_hint(message)
        confidence = calculate_classification_confidence(message, category, entities)

        explanation = (
            f"Classified as '{category}' with confidence {confidence:.2f} based on domain keywords "
            f"and extracted entities: {list(k for k, v in entities.items() if v)}."
        )

        classification_data = {
            "category": category,
            "confidence": confidence,
            "entities": entities,
            "explanation": explanation,
        }

        # Update Blackboard
        blackboard.update_section("classification", classification_data)
        blackboard.set_status("CLASSIFIED")

        # Record in Event Log
        event_log.append_event(
            ticket_id=ticket_id,
            agent="ClassifierAgent",
            action="TicketClassified",
            status="SUCCESS",
            details={
                "category": category,
                "confidence": confidence,
                "entities_found": {k: v for k, v in entities.items() if v},
            },
        )

        return classification_data
