"""
Append-Only Auditable Event Log for Agent Execution Traces.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass(frozen=True)
class Event:
    event_id: str
    ticket_id: str
    timestamp: str
    agent: str
    action: str
    status: str
    details: Dict[str, Any]


class EventLog:
    """
    Append-only execution trace logger.
    Events cannot be edited or removed once appended.
    """

    def __init__(self):
        self._events: List[Event] = []
        self._counter: int = 0

    def append_event(
        self,
        ticket_id: str,
        agent: str,
        action: str,
        status: str = "SUCCESS",
        details: Dict[str, Any] | None = None,
    ) -> Event:
        self._counter += 1
        event_id = f"EVT-{self._counter:04d}"
        timestamp = datetime.now(timezone.utc).isoformat()

        event = Event(
            event_id=event_id,
            ticket_id=ticket_id,
            timestamp=timestamp,
            agent=agent,
            action=action,
            status=status,
            details=details or {},
        )
        self._events.append(event)
        return event

    def get_events(self, ticket_id: str | None = None) -> List[Event]:
        if ticket_id is None:
            return list(self._events)
        return [e for e in self._events if e.ticket_id == ticket_id]

    def to_list(self, ticket_id: str | None = None) -> List[Dict[str, Any]]:
        return [asdict(e) for e in self.get_events(ticket_id)]

    def to_json(self, ticket_id: str | None = None, indent: int = 2) -> str:
        return json.dumps(self.to_list(ticket_id), indent=indent, default=str)

    def __len__(self) -> int:
        return len(self._events)
