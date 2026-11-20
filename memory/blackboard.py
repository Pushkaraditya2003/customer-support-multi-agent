"""
Shared Blackboard System for Collaborative Multi-Agent State.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class Blackboard:
    """
    Central shared blackboard where all agents read and write ticket state.
    Provides isolated, observable, and thread-safe dictionary snapshots.
    """

    def __init__(self, ticket_id: str, customer_id: str, customer_message: str):
        self._state: Dict[str, Any] = {
            "ticket_id": ticket_id,
            "customer_id": customer_id,
            "customer_message": customer_message,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "status": "RECEIVED",  # RECEIVED, CLASSIFIED, ROUTED, SPECIALIST_PROCESSED, REVIEWED, REVISED, ESCALATED, RESOLVED
            "classification": {
                "category": None,        # billing, technical, account, other
                "confidence": 0.0,
                "entities": {},
                "explanation": None,
            },
            "routing": {
                "target_specialist": None, # billing_specialist, technical_specialist, account_specialist, escalation_router
                "route_type": None,        # SPECIALIST or ESCALATION
                "reason": None,
            },
            "specialist_output": {
                "specialist_name": None,
                "resolution": None,
                "evidence": [],
                "is_resolved": False,
                "needs_escalation": False,
                "metadata": {},
            },
            "escalation": {
                "is_escalated": False,
                "reason": None,
                "priority": "NORMAL",      # NORMAL, HIGH, URGENT
                "target_tier": None,       # Tier 2 Billing, Tier 2 Engineering, Trust & Safety
            },
            "draft_response": None,
            "review": {
                "approved": False,
                "tone_score": 0.0,
                "completeness_score": 0.0,
                "feedback": [],
                "revision_count": 0,
            },
            "final_response": None,
        }

    @property
    def ticket_id(self) -> str:
        return self._state["ticket_id"]

    @property
    def customer_id(self) -> str:
        return self._state["customer_id"]

    @property
    def status(self) -> str:
        return self._state["status"]

    def set_status(self, new_status: str) -> None:
        self._state["status"] = new_status
        self._state["updated_at"] = datetime.now(timezone.utc).isoformat()

    def update_section(self, section: str, data: Dict[str, Any]) -> None:
        """Update a specific section on the blackboard with dictionary data."""
        if section not in self._state:
            self._state[section] = {}
        if isinstance(self._state[section], dict):
            self._state[section].update(data)
        else:
            self._state[section] = data
        self._state["updated_at"] = datetime.now(timezone.utc).isoformat()

    def set_value(self, key: str, value: Any) -> None:
        """Set a top-level property on the blackboard."""
        self._state[key] = value
        self._state["updated_at"] = datetime.now(timezone.utc).isoformat()

    def get_value(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def get_section(self, section: str) -> Dict[str, Any]:
        val = self._state.get(section, {})
        return copy.deepcopy(val) if isinstance(val, dict) else val

    def snapshot(self) -> Dict[str, Any]:
        """Return an immutable deepcopy snapshot of current state."""
        return copy.deepcopy(self._state)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self._state, indent=indent, default=str)
