"""
Session and Conversation Memory for Multi-turn Ticket Follow-ups.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class SessionMemory:
    """
    Manages historical context across tickets and conversational turns for customers.
    Allows agents to recall past tickets, categories, and resolutions.
    """

    def __init__(self):
        # Maps customer_id -> list of historical ticket summary records
        self._customer_records: Dict[str, List[Dict[str, Any]]] = {}
        # Maps ticket_id -> full ticket snapshot
        self._ticket_store: Dict[str, Dict[str, Any]] = {}

    def record_ticket(self, ticket_snapshot: Dict[str, Any]) -> None:
        """Store a completed or in-progress ticket snapshot in memory."""
        ticket_id = ticket_snapshot["ticket_id"]
        customer_id = ticket_snapshot["customer_id"]

        self._ticket_store[ticket_id] = ticket_snapshot

        if customer_id not in self._customer_records:
            self._customer_records[customer_id] = []

        # Update existing record if ticket already listed, else append
        existing = next(
            (item for item in self._customer_records[customer_id] if item["ticket_id"] == ticket_id),
            None,
        )
        summary = {
            "ticket_id": ticket_id,
            "created_at": ticket_snapshot.get("created_at"),
            "status": ticket_snapshot.get("status"),
            "category": ticket_snapshot.get("classification", {}).get("category"),
            "target_specialist": ticket_snapshot.get("routing", {}).get("target_specialist"),
            "final_response": ticket_snapshot.get("final_response"),
            "is_escalated": ticket_snapshot.get("escalation", {}).get("is_escalated", False),
        }

        if existing:
            existing.update(summary)
        else:
            self._customer_records[customer_id].append(summary)

    def get_customer_history(self, customer_id: str) -> List[Dict[str, Any]]:
        """Return ticket history summaries for a specific customer."""
        return list(self._customer_records.get(customer_id, []))

    def get_latest_ticket(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent ticket snapshot for a customer."""
        history = self._customer_records.get(customer_id, [])
        if not history:
            return None
        latest_id = history[-1]["ticket_id"]
        return self._ticket_store.get(latest_id)

    def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        return self._ticket_store.get(ticket_id)

    def build_history_context(self, customer_id: str, max_tickets: int = 3) -> str:
        """Format recent customer interactions into a clear textual context."""
        history = self.get_customer_history(customer_id)[-max_tickets:]
        if not history:
            return "No previous ticket history on record for this customer."

        lines = [f"Customer {customer_id} Previous Interaction History:"]
        for idx, rec in enumerate(history, 1):
            status = rec.get("status", "UNKNOWN")
            cat = rec.get("category", "unclassified")
            tid = rec.get("ticket_id")
            resp = rec.get("final_response") or "Pending"
            short_resp = (resp[:120] + "...") if len(resp) > 120 else resp
            lines.append(
                f"- Ticket [{tid}] ({cat}): Status={status}. Resolution Summary: {short_resp}"
            )
        return "\n".join(lines)
