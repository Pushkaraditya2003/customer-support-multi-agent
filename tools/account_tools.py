"""
Account Specialist Tools: Account authentication, security status, and credential resets.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict


def verify_account_security_status(account_id: str, email: str = "") -> Dict[str, Any]:
    """
    Check account security flags, lockout state, and active authentication policies.
    """
    acc = account_id.strip() if account_id else "ACC-GUEST"
    em = email.strip() if email else "unspecified@enterprise.com"

    # Deterministic simulation of account security database record
    is_compromised = "compromised" in acc.lower() or "hacked" in em.lower()
    is_locked = "locked" in acc.lower() or "blocked" in em.lower() or is_compromised

    status = "COMPROMISED" if is_compromised else ("LOCKED" if is_locked else "ACTIVE")

    return {
        "account_id": acc,
        "email": em,
        "status": status,
        "is_locked": is_locked,
        "is_compromised": is_compromised,
        "two_factor_auth_enabled": True,
        "consecutive_failed_logins": 5 if is_locked else 0,
        "risk_level": "CRITICAL" if is_compromised else ("MEDIUM" if is_locked else "LOW"),
        "recommended_action": (
            "Account compromised! Revoke active session tokens immediately and trigger security verification."
            if is_compromised
            else (
                "Account locked due to consecutive authentication failures. Issue timed unlock link."
                if is_locked
                else "Account is in healthy standing."
            )
        ),
    }


def initiate_secure_password_reset(
    account_id: str, email: str = "", delivery_channel: str = "EMAIL"
) -> Dict[str, Any]:
    """
    Trigger time-limited, cryptographically random password reset procedure.
    """
    acc = account_id.strip() if account_id else "ACC-GUEST"
    token_id = f"RST-{uuid.uuid4().hex[:12].upper()}"

    return {
        "account_id": acc,
        "reset_token_id": token_id,
        "delivery_channel": delivery_channel.upper(),
        "delivery_target": email or "primary registered security email",
        "validity_minutes": 15,
        "instructions": (
            f"A one-time secure password reset link (Token: {token_id}) has been dispatched to {delivery_channel}. "
            "Link expires strictly in 15 minutes. For security, all other active sessions have been terminated."
        ),
    }
