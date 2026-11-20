"""
Technical Specialist Tools: RAG knowledge search and error diagnostics.
"""

from __future__ import annotations

from typing import Any, Dict, List
from config import KB_DIR, SIMILARITY_THRESHOLD
from rag.retriever import LocalVectorRetriever

# Lazy-loaded singleton retriever instance
_RETRIEVER: LocalVectorRetriever | None = None


def get_retriever() -> LocalVectorRetriever:
    global _RETRIEVER
    if _RETRIEVER is None:
        _RETRIEVER = LocalVectorRetriever(kb_dir=KB_DIR)
    return _RETRIEVER


def query_technical_knowledge_base(
    query: str, top_k: int = 3, min_similarity: float = SIMILARITY_THRESHOLD
) -> Dict[str, Any]:
    """
    Perform local semantic vector search against official support documentation.
    """
    retriever = get_retriever()
    context_text, sources, sufficient = retriever.get_context(
        query=query, top_k=top_k, min_similarity=min_similarity
    )

    return {
        "query": query,
        "context": context_text,
        "sources": sources,
        "sufficient_evidence": sufficient,
        "citations_count": len(sources),
    }


def diagnose_error_code(error_code: str) -> Dict[str, Any]:
    """
    Deterministic catalog lookup for standard error codes.
    """
    code = error_code.strip().upper()
    catalog = {
        "ERR-1001": {
            "title": "Gateway Request Timeout",
            "root_cause": "Upstream microservice timed out after 30 seconds due to backlog.",
            "remediation": "Instruct user to wait 60 seconds and retry with exponential backoff. Check system status page.",
            "requires_escalation": False,
            "source": "[error_codes.txt#ERR-1001]",
        },
        "ERR-1002": {
            "title": "Unauthorized API Call / Expired Token",
            "root_cause": "Session JWT has lapsed or was revoked after IP shift.",
            "remediation": "Prompt user to perform full browser logout, clear '.enterprise-desk.com' cookies, and log in via SSO.",
            "requires_escalation": False,
            "source": "[error_codes.txt#ERR-1002]",
        },
        "ERR-2005": {
            "title": "Database Sync Conflict",
            "root_cause": "Simultaneous optimistic write conflict on same record.",
            "remediation": "Hard refresh ticket view to reload latest record revision and reapply update.",
            "requires_escalation": False,
            "source": "[error_codes.txt#ERR-2005]",
        },
        "ERR-4030": {
            "title": "API Rate Limit Exceeded",
            "root_cause": "Request frequency exceeded 120 calls per minute.",
            "remediation": "Enforce client-side rate throttling; request enterprise high-volume tier whitelisting.",
            "requires_escalation": False,
            "source": "[error_codes.txt#ERR-4030]",
        },
    }

    if code in catalog:
        item = catalog[code]
        return {
            "found": True,
            "error_code": code,
            "title": item["title"],
            "root_cause": item["root_cause"],
            "remediation": item["remediation"],
            "source": item["source"],
        }

    return {
        "found": False,
        "error_code": code,
        "title": "Unknown Error Code",
        "root_cause": "Error code is not cataloged in standard documentation.",
        "remediation": "Requires technical log analysis by engineering.",
        "source": "None",
    }
