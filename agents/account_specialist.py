"""
Agent 4: Account Specialist
Handles login failures, password resets, account lockout, and 2FA recovery.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from semantic_kernel.functions import kernel_function

from tools.account_tools import verify_account_security_status, initiate_secure_password_reset
from memory.blackboard import Blackboard
from memory.event_log import EventLog


class AccountPlugin:
    """Semantic Kernel plugin for account authentication and security operations."""

    @kernel_function(
        name="verify_security",
        description="Inspect account lockout state, 2FA status, and risk level.",
    )
    def verify_security(self, account_id: str, email: str = "") -> str:
        res = verify_account_security_status(account_id, email)
        return json.dumps(res)

    @kernel_function(
        name="initiate_reset",
        description="Dispatch a cryptographically secure one-time password reset link.",
    )
    def initiate_reset(self, account_id: str, email: str = "") -> str:
        res = initiate_secure_password_reset(account_id, email)
        return json.dumps(res)


class AccountSpecialist:
    """
    Account Specialist Agent responsible for authentication troubleshooting,
    secure credential resets, and account lockout remediation.
    """

    def __init__(self, kernel: Optional[Any] = None):
        self.kernel = kernel
        self.plugin = AccountPlugin()
        if self.kernel:
            self.kernel.add_plugin(self.plugin, plugin_name="account_tools")

    def process(self, blackboard: Blackboard, event_log: EventLog) -> Dict[str, Any]:
        ticket_id = blackboard.ticket_id
        message = blackboard.get_value("customer_message")
        entities = blackboard.get_section("classification").get("entities", {})

        acc_id = entities.get("account_ids", ["ACC-CURRENT"])[0] if entities.get("account_ids") else "ACC-USER"
        email = entities.get("emails", ["customer@enterprise.com"])[0] if entities.get("emails") else "registered security email"

        # Check for compromise keywords
        is_hacked = any(w in message.lower() for w in ["compromised", "hacked", "stolen", "unauthorized access"])
        if is_hacked:
            acc_id = f"{acc_id}-compromised"

        # Execute genuine account tools
        sec_status = verify_account_security_status(account_id=acc_id, email=email)
        reset_action = initiate_secure_password_reset(account_id=acc_id, email=email)

        is_resolved = not sec_status["is_compromised"]
        needs_escalation = sec_status["is_compromised"]

        if sec_status["is_compromised"]:
            draft_response = (
                f"Hello, thank you for urgently contacting Enterprise Account Security.\n\n"
                f"We take account security very seriously. Because your report indicates potential unauthorized "
                f"account access, we have immediately locked your account credentials and terminated all active sessions. "
                f"We have escalated your case to our Trust & Safety / Account Security team for high-priority identity verification.\n\n"
                f"A specialized security representative will contact you via your verified secondary channel to safely restore your access."
            )
            resolution_notes = "Account marked COMPROMISED. Sessions revoked. Escalated to Trust & Safety."
        else:
            draft_response = (
                f"Hello, thank you for reaching out to Enterprise Account Support.\n\n"
                f"We have verified the security status for account {acc_id}. "
                f"{sec_status['recommended_action']}\n\n"
                f"Next Steps to Access Your Account:\n"
                f"1. {reset_action['instructions']}\n"
                f"2. Once reset, ensure Two-Factor Authentication (2FA) is re-confirmed in your Profile Settings.\n\n"
                f"If you did not request this recovery or encounter further login friction, please notify our team immediately."
            )
            resolution_notes = f"Account verified. Reset token {reset_action['reset_token_id']} issued."

        specialist_data = {
            "specialist_name": "AccountSpecialist",
            "resolution": resolution_notes,
            "evidence": [f"Status: {sec_status['status']}", f"Risk: {sec_status['risk_level']}"],
            "is_resolved": is_resolved,
            "needs_escalation": needs_escalation,
            "metadata": {
                "security_status": sec_status,
                "reset_token": reset_action["reset_token_id"],
            },
        }

        # Update Blackboard
        blackboard.update_section("specialist_output", specialist_data)
        blackboard.set_value("draft_response", draft_response)
        blackboard.set_status("SPECIALIST_PROCESSED")

        # Record in Event Log
        event_log.append_event(
            ticket_id=ticket_id,
            agent="AccountSpecialist",
            action="AccountSecurityEvaluated",
            status="SUCCESS" if is_resolved else "ESCALATED",
            details={
                "account_id": acc_id,
                "status": sec_status["status"],
                "risk_level": sec_status["risk_level"],
                "needs_escalation": needs_escalation,
            },
        )

        return specialist_data
