"""
Main Entry Point for Enterprise Customer Support Triage and Resolution Desk.
Course: CSE476 - Agentic AI and Intelligent Automation (CA2)
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from memory.session_memory import SessionMemory
from orchestration.workflow import SupportDeskOrchestrator


def print_banner() -> None:
    print("=" * 75)
    print("   ENTERPRISE CUSTOMER SUPPORT TRIAGE AND RESOLUTION DESK (CA2)   ")
    print("   Multi-Agent Collaborative System - Group 3                      ")
    print("=" * 75)


def display_ticket_result(result: dict) -> None:
    snap = result["blackboard_snapshot"]
    classification = snap.get("classification", {})
    routing = snap.get("routing", {})
    specialist = snap.get("specialist_output", {})
    escalation = snap.get("escalation", {})
    review = snap.get("review", {})

    print(f"\n[Ticket ID]: {result['ticket_id']} | Status: {result['status']}")
    print(f"[Customer Message]: {snap.get('customer_message')}")
    print("-" * 75)
    print(f"[Classification]: Category={classification.get('category')} | Confidence={classification.get('confidence'):.2f}")
    if classification.get("entities"):
        found_ents = {k: v for k, v in classification['entities'].items() if v}
        if found_ents:
            print(f"[Entities Detected]: {found_ents}")
    print(f"[Routing]: Route={routing.get('target_specialist')} | Type={routing.get('route_type')} | Reason={routing.get('reason')}")
    
    if specialist.get("specialist_name"):
        print(f"[Specialist]: {specialist.get('specialist_name')} | Resolved={specialist.get('is_resolved')} | NeedsEscalation={specialist.get('needs_escalation')}")
        if specialist.get("evidence"):
            print(f"[Evidence / Citations]: {specialist.get('evidence')}")

    if escalation.get("is_escalated"):
        print(f"[Human Escalation]: Priority={escalation.get('priority')} | Target Queue={escalation.get('target_tier')}")
        print(f"[Escalation Reason]: {escalation.get('reason')}")

    print(f"[Quality Review]: Approved={review.get('approved')} | Tone={review.get('tone_score')} | Completeness={review.get('completeness_score')} | Revisions={review.get('revision_count')}")
    print("=" * 75)
    print("[FINAL CUSTOMER RESPONSE]:")
    print(result["final_response"])
    print("=" * 75)


def run_interactive_mode() -> None:
    print_banner()
    print("Interactive Session Mode. Type 'exit' or 'quit' to end.\n")

    session_mem = SessionMemory()
    orchestrator = SupportDeskOrchestrator(session_memory=session_mem)
    customer_id = "CUST-1001"

    while True:
        try:
            print("\nEnter customer ticket / query: ", end="", flush=True)
            line = sys.stdin.readline()
            if not line:
                break
            user_msg = line.strip()
            if not user_msg:
                continue
            if user_msg.lower() in ["exit", "quit", "q"]:
                print("\nEnding session. Goodbye!")
                break

            # Handle follow-up query detection
            if any(w in user_msg.lower() for w in ["previous ticket", "status of my", "my earlier", "last issue", "who is handling"]):
                history_ctx = session_mem.build_history_context(customer_id)
                print(f"\n[Session Memory Recalled]:\n{history_ctx}\n")

            result = orchestrator.process_ticket(customer_message=user_msg, customer_id=customer_id)
            display_ticket_result(result)

        except KeyboardInterrupt:
            print("\nSession interrupted. Exiting.")
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="CA2 Enterprise Customer Support Multi-Agent Desk")
    parser.add_argument("--message", "-m", type=str, help="Single customer ticket message to process")
    parser.add_argument("--customer-id", "-c", type=str, default="CUST-1001", help="Customer identifier")
    parser.add_argument("--audit-log", action="store_true", help="Print complete auditable event log")
    args = parser.parse_args()

    if args.message:
        print_banner()
        orchestrator = SupportDeskOrchestrator()
        result = orchestrator.process_ticket(customer_message=args.message, customer_id=args.customer_id)
        display_ticket_result(result)
        if args.audit_log:
            print("\n[AUDITABLE EVENT LOG]:")
            print(json.dumps(result["event_log"], indent=2))
    else:
        run_interactive_mode()


if __name__ == "__main__":
    main()
