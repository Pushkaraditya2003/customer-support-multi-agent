"""
Reviewer Agent Tools: Response quality, completeness, tone, and compliance verification.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


def validate_response_quality(
    draft_text: str,
    category: str,
    is_escalated: bool = False,
    sources_cited: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Evaluate draft customer reply against professional support standards.
    Checks:
    - Minimum reasonable length (> 20 words)
    - Empathy / greeting presence
    - Actionable guidance
    - Evidence / citations present for technical answers
    - Clear escalation notification if escalated
    """
    sources_cited = sources_cited or []
    feedback: List[str] = []
    text = draft_text.strip()
    words = text.split()

    if len(words) < 15:
        feedback.append("Response is excessively terse (under 15 words). Needs more context and helpful explanation.")

    # Greeting / Courtesy check
    greetings = ["hello", "hi", "dear", "thank you", "thanks", "greetings"]
    has_greeting = any(g in text.lower() for g in greetings)
    if not has_greeting:
        feedback.append("Missing professional greeting or courtesy expression.")

    # Tone check: Avoid blame words
    blame_words = ["your fault", "you failed to", "you broke", "obviously", "stupid"]
    for bw in blame_words:
        if bw in text.lower():
            feedback.append(f"Unempathetic or accusatory phrasing detected: '{bw}'.")

    # Technical citation check
    if category == "technical" and not is_escalated and not sources_cited and "[" not in text:
        feedback.append("Technical response is missing documented source citations or knowledge base references.")

    # Escalation notice check
    if is_escalated:
        escalation_terms = ["escalat", "human", "specialist team", "tier 2", "reviewing your case", "representative"]
        if not any(term in text.lower() for term in escalation_terms):
            feedback.append("Ticket is escalated to human staff, but the draft does not clearly inform the customer.")

    # Compute scores
    tone_deductions = len([f for f in feedback if "tone" in f.lower() or "courtesy" in f.lower() or "accusatory" in f.lower()]) * 0.25
    tone_score = max(0.0, 1.0 - tone_deductions)

    comp_deductions = len([f for f in feedback if "terse" in f.lower() or "citation" in f.lower() or "escalat" in f.lower()]) * 0.30
    completeness_score = max(0.0, 1.0 - comp_deductions)

    approved = (len(feedback) == 0)

    return {
        "approved": approved,
        "tone_score": round(tone_score, 2),
        "completeness_score": round(completeness_score, 2),
        "feedback": feedback,
    }


def check_compliance_and_safety(draft_text: str) -> Dict[str, Any]:
    """
    Scan draft for disallowed false promises or security violations.
    """
    flags: List[str] = []
    text_lower = draft_text.lower()

    # Disallowed promises
    if "i promise 100%" in text_lower or "guarantee you will get money back immediately" in text_lower:
        flags.append("Unauthorized absolute financial commitment detected.")

    if "your password is" in text_lower or "send me your plain password" in text_lower:
        flags.append("Security violation: asking for or sending plaintext credentials.")

    return {
        "compliant": len(flags) == 0,
        "flags": flags,
    }
