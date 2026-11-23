"""
Enterprise Customer Support Triage and Resolution Desk - Streamlit Frontend
Course: CSE476 - Agentic AI and Intelligent Automation (CA2 - Multi-Agent System)
Selected Topic: Group 3 - Enterprise Customer Support Triage and Resolution Desk
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Ensure ca2 directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    CONFIDENCE_THRESHOLD,
    GROQ_MODEL,
    MAX_REVISION_ATTEMPTS,
    PROVIDER,
    SIMILARITY_THRESHOLD,
)
from memory.session_memory import SessionMemory
from orchestration.workflow import SupportDeskOrchestrator
from rag.retriever import LocalVectorRetriever

# Page Setup
st.set_page_config(
    page_title="Enterprise Customer Support Desk (CA2)",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .badge-resolved {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-escalated {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Initialize Session State
if "session_memory" not in st.session_state:
    st.session_state.session_memory = SessionMemory()

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = SupportDeskOrchestrator(
        session_memory=st.session_state.session_memory
    )

if "latest_result" not in st.session_state:
    st.session_state.latest_result = None

if "input_ticket" not in st.session_state:
    st.session_state.input_ticket = ""

if "customer_id" not in st.session_state:
    st.session_state.customer_id = "CUST-1001"


# Preset Scenarios
PRESETS = {
    "Select a Preset Scenario...": "",
    "Scenario 1: Billing Issue (Refund & Order Confirmation Delay)": (
        "My payment of $49.99 was deducted from my account, but my order was not confirmed. "
        "I have already waited for two hours. Order ORD-9912, transaction TXN-5544."
    ),
    "Scenario 2: Technical Error (ERR-1001 Gateway Timeout with RAG)": (
        "The web console is throwing an ERR-1001 gateway request timeout error when querying the analytics dashboard."
    ),
    "Scenario 3: Account Security (Account Lockout & Reset)": (
        "I am locked out of my account ACC-8822 after entering the wrong password multiple times. Please help me reset access."
    ),
    "Scenario 4: Insufficient Knowledge Base Evidence -> Human Escalation": (
        "I have a problem with a proprietary holographic rendering firmware that is not covered in your support documentation."
    ),
    "Scenario 5: Out-of-Domain Query ('Other' Category -> Escalation)": (
        "Can you send someone to repaint my front porch blue tomorrow morning?"
    ),
    "Scenario 6: Multi-Turn Follow-Up (Querying Prior Ticket Memory)": (
        "Can you tell me which specialist handled my earlier payment issue and what was the resolution?"
    ),
}


# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown("### 🏢 System Architecture")
    st.caption("**CSE476 CA2 – Multi-Agent System (Group 3)**")

    st.markdown("---")
    st.markdown("#### ⚡ Quick Preset Scenarios")
    selected_preset = st.selectbox(
        "Load an evaluation scenario:",
        list(PRESETS.keys()),
        index=0,
    )
    if selected_preset != "Select a Preset Scenario..." and PRESETS[selected_preset]:
        if st.button("📥 Load Preset into Ticket Box", use_container_width=True):
            st.session_state.input_ticket = PRESETS[selected_preset]
            st.rerun()

    st.markdown("---")
    st.markdown("#### ⚙️ Configuration & Model")
    st.text(f"Provider: {PROVIDER.upper()}")
    st.text(f"LLM: {GROQ_MODEL}")
    st.text(f"Framework: Semantic Kernel 1.44")
    st.text(f"Confidence Threshold: {CONFIDENCE_THRESHOLD}")
    st.text(f"Similarity Threshold: {SIMILARITY_THRESHOLD}")
    st.text(f"Max Review Revisions: {MAX_REVISION_ATTEMPTS}")

    st.markdown("---")
    st.markdown("#### 👥 Active Specialized Agents")
    st.markdown(
        """
        1. **Classifier Agent** *(Domain & Entities)*
        2. **Billing Specialist** *(Financial Rules)*
        3. **Technical Specialist** *(Local RAG)*
        4. **Account Specialist** *(Security & 2FA)*
        5. **Escalation Router** *(Human Queues)*
        6. **Reviewer Agent** *(QA & Revision)*
        """
    )

    st.markdown("---")
    if st.button("🔄 Reset Session Memory", use_container_width=True):
        st.session_state.session_memory = SessionMemory()
        st.session_state.orchestrator = SupportDeskOrchestrator(
            session_memory=st.session_state.session_memory
        )
        st.session_state.latest_result = None
        st.session_state.input_ticket = ""
        st.success("Session memory cleared!")
        st.rerun()


# ==============================================================================
# MAIN PAGE
# ==============================================================================
st.markdown('<div class="main-header">🎧 Enterprise Customer Support Desk</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Collaborative Multi-Agent Triage, Resolution & Escalation Desk · Router-to-Specialists Architecture</div>',
    unsafe_allow_html=True,
)

# Ticket Submission Form
col_input, col_meta = st.columns([4, 1])

with col_meta:
    cust_id_input = st.text_input("Customer ID:", value=st.session_state.customer_id)
    st.session_state.customer_id = cust_id_input

with col_input:
    user_ticket = st.text_area(
        "Enter Customer Support Ticket or Follow-up Query:",
        value=st.session_state.input_ticket,
        height=100,
        placeholder="Type or paste a customer complaint, error code, billing issue, or follow-up...",
    )

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    submit_clicked = st.button("🚀 Process Ticket", type="primary", use_container_width=True)

# Process Ticket Execution
if submit_clicked and user_ticket.strip():
    with st.status("🤖 Coordinating Multi-Agent Workflow...", expanded=True) as status_box:
        st.write("📥 **Ingestion:** Initializing shared Blackboard and Event Log...")
        
        # Check follow-up memory
        is_followup = any(
            w in user_ticket.lower()
            for w in ["previous ticket", "status of my", "my earlier", "last issue", "who is handling"]
        )
        if is_followup:
            st.write("🧠 **Session Memory:** Recalling customer interaction history...")

        st.write("🔍 **Classifier Agent:** Categorizing issue and extracting structured entities...")
        st.write("🔀 **Main Router:** Evaluating confidence and selecting specialized agent queue...")
        st.write("🛠️ **Specialist Execution:** Executing domain rules / searching local RAG knowledge base...")
        st.write("⚖️ **Escalation Check:** Validating resolution completeness and evidence sufficiency...")
        st.write("📝 **Reviewer Agent:** Auditing tone, courtesy, completeness, and compliance (revision loop)...")
        
        # Run orchestrator
        result = st.session_state.orchestrator.process_ticket(
            customer_message=user_ticket.strip(),
            customer_id=st.session_state.customer_id,
        )
        st.session_state.latest_result = result
        st.session_state.input_ticket = user_ticket.strip()
        status_box.update(label="✅ Ticket Processing Completed!", state="complete", expanded=False)


# ==============================================================================
# RESULTS DISPLAY
# ==============================================================================
if st.session_state.latest_result:
    res = st.session_state.latest_result
    snap = res["blackboard_snapshot"]
    classification = snap.get("classification", {})
    routing = snap.get("routing", {})
    specialist = snap.get("specialist_output", {})
    escalation = snap.get("escalation", {})
    review = snap.get("review", {})
    is_escalated = escalation.get("is_escalated", False)

    st.markdown("---")
    
    # Header Banner
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.markdown(f"### 📋 Ticket: `{res['ticket_id']}`")
    with col_t2:
        if is_escalated:
            st.markdown('<div style="text-align:right;"><span class="badge-escalated">⚠️ ESCALATED TO HUMAN</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:right;"><span class="badge-resolved">✅ RESOLVED AUTOMATICALLY</span></div>', unsafe_allow_html=True)

    # Key Metrics Bar
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Category", str(classification.get("category", "N/A")).title())
    with m2:
        conf_val = classification.get("confidence", 0.0)
        st.metric("Confidence", f"{conf_val * 100:.0f}%")
    with m3:
        target_spec = routing.get("target_specialist", "N/A").replace("_", " ").title()
        st.metric("Assigned Route", target_spec)
    with m4:
        tone_val = review.get("tone_score", 0.0)
        st.metric("Tone Rating", f"{tone_val * 100:.0f}%")
    with m5:
        rev_count = review.get("revision_count", 0)
        st.metric("QA Revisions", f"{rev_count} / {MAX_REVISION_ATTEMPTS}")

    # Tabs for in-depth inspection
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "💬 Final Customer Response",
            "🧩 Multi-Agent Breakdown",
            "📚 Local RAG Inspector",
            "🗃️ Shared Blackboard",
            "📜 Auditable Event Log",
        ]
    )

    # TAB 1: Final Customer Response
    with tab1:
        st.markdown("#### Official Customer Reply")
        st.info(res["final_response"])

        if is_escalated:
            st.warning(
                f"**Human Escalation Notice:**\n"
                f"- **Target Queue:** {escalation.get('target_tier')}\n"
                f"- **Priority Level:** {escalation.get('priority')}\n"
                f"- **Primary Reason:** {escalation.get('reason')}\n\n"
                f"**Internal Staff Briefing Note:**\n```\n{escalation.get('handoff_note')}\n```"
            )

    # TAB 2: Multi-Agent Architecture Breakdown
    with tab2:
        st.markdown("#### Step-by-Step Agent Collaboration Trace")
        
        with st.expander("1. Classifier Agent Output", expanded=True):
            st.write(f"**Assigned Category:** `{classification.get('category')}`")
            st.write(f"**Confidence Score:** `{classification.get('confidence'):.2f}`")
            st.write(f"**Rationale:** {classification.get('explanation')}")
            entities = classification.get("entities", {})
            found_ents = {k: v for k, v in entities.items() if v}
            if found_ents:
                st.write("**Extracted Entities:**", found_ents)

        with st.expander("2. Main Router Decision", expanded=True):
            st.write(f"**Target Specialist Queue:** `{routing.get('target_specialist')}`")
            st.write(f"**Routing Type:** `{routing.get('route_type')}`")
            st.write(f"**Routing Rule Rationale:** {routing.get('reason')}")

        with st.expander("3. Specialist Execution Details", expanded=True):
            st.write(f"**Specialist:** `{specialist.get('specialist_name')}`")
            st.write(f"**Resolution Note:** {specialist.get('resolution')}")
            st.write(f"**Automated Resolution Achieved:** `{specialist.get('is_resolved')}`")
            st.write(f"**Needs Escalation:** `{specialist.get('needs_escalation')}`")
            if specialist.get("evidence"):
                st.write("**Supporting Evidence / Citations:**", specialist.get("evidence"))
            if specialist.get("metadata"):
                st.json(specialist.get("metadata"))

        with st.expander("4. Reviewer Agent Quality Assessment", expanded=True):
            st.write(f"**Approved:** `{review.get('approved')}`")
            st.write(f"**Tone Score:** `{review.get('tone_score'):.2f} / 1.0`")
            st.write(f"**Completeness Score:** `{review.get('completeness_score'):.2f} / 1.0`")
            st.write(f"**Revision Cycles Taken:** `{review.get('revision_count')}`")
            if review.get("feedback"):
                st.write("**QA Feedback Log:**", review.get("feedback"))
            else:
                st.write("✅ **QA Feedback:** All professional courtesy, tone, and compliance standards met.")

    # TAB 3: Local RAG Knowledge Base Inspector
    with tab3:
        st.markdown("#### Local Vector Knowledge Base Retrieval (Technical Specialist Only)")
        evidence_list = specialist.get("evidence", [])
        if evidence_list:
            st.success(f"Retrieved {len(evidence_list)} grounded references from local knowledge base.")
            for ev in evidence_list:
                st.markdown(f"- 📄 **Document Source:** `{ev}`")
        else:
            if classification.get("category") == "technical":
                st.warning("⚠️ RAG Search: Insufficient semantic similarity found in knowledge base. Automated hallucination was rejected and ticket was escalated.")
            else:
                st.info("ℹ️ RAG was not invoked for this ticket (RAG is strictly scoped to Technical Specialist inquiries).")

    # TAB 4: Shared Blackboard
    with tab4:
        st.markdown("#### Central Blackboard Snapshot")
        st.caption("All agents read from and write to this single observable state.")
        st.json(snap)

    # TAB 5: Auditable Event Log
    with tab5:
        st.markdown("#### Append-Only Chronological Execution Trail")
        st.caption("Immutable record of all transitions, agent actions, and timestamps.")
        events = res["event_log"]
        if events:
            df_events = pd.DataFrame(events)
            st.dataframe(
                df_events[["timestamp", "event_id", "agent", "action", "status"]],
                use_container_width=True,
                hide_index=True,
            )
            with st.expander("View Raw Event Payloads (JSON)"):
                st.json(events)

    # Multi-turn conversation context display
    cust_history = st.session_state.session_memory.get_customer_history(st.session_state.customer_id)
    if len(cust_history) > 1:
        st.markdown("---")
        st.markdown(f"#### 🧠 Customer `{st.session_state.customer_id}` Session Memory History ({len(cust_history)} Tickets)")
        for idx, h in enumerate(reversed(cust_history), 1):
            st.markdown(
                f"- **Ticket [{h['ticket_id']}]** ({str(h.get('category')).upper()}): Status=`{h['status']}`, "
                f"Specialist=`{h.get('target_specialist')}`. Response: *{str(h.get('final_response'))[:120]}...*"
            )
