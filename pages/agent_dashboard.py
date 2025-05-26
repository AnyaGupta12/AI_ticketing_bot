# File: pages/agent_dashboard.py
import streamlit as st
import sqlite3
from db import get_conn

def agent_dashboard():
    # Ensure login
    if "user_id" not in st.session_state or "user_name" not in st.session_state:
        st.error("Please log in to access the agent dashboard.")
        st.stop()

    st.markdown(
        f"<h2 style='text-align: center;'>Agent Dashboard ({st.session_state['user_name']})</h2>",
        unsafe_allow_html=True
    )

    agent_id = st.session_state["user_id"]
    company_id = st.session_state.get("company_id")

    conn = get_conn()
    c = conn.cursor()

    # Load all open handoff tickets for this agent's company
    c.execute("""
        SELECT id, product, priority, problem_description, contact_name, contact_email
          FROM Tickets
         WHERE company_id = ? AND status = 'Handoff'
         ORDER BY created_at DESC
    """, (company_id,))
    tickets = c.fetchall()

    if not tickets:
        st.success("✅ No handoff tickets at the moment.")
        return

    st.markdown("### 📨 Handoff Tickets Needing Attention")

    for ticket in tickets:
        ticket_id, product, priority, desc, contact_name, contact_email = ticket

        with st.expander(f"Ticket #{ticket_id} - {product} [{priority}]"):
            st.warning("🚩 This ticket was flagged by AI for human review.")
            st.markdown(f"**Submitted by:** `{contact_name}` ({contact_email})")
            st.markdown(f"**Issue Description:** {desc}")

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("💬 Join Chat", key=f"join_{ticket_id}"):
                    st.session_state["current_ticket_id"] = ticket_id
                    st.switch_page("pages/agent_chat.py")

            with col2:
                if st.button("✅ Mark as Resolved", key=f"resolve_{ticket_id}"):
                    c.execute("""
                        UPDATE Tickets
                           SET status = 'Closed', user_id = ?
                         WHERE id = ?
                    """, (agent_id, ticket_id))
                    conn.commit()
                    st.success(f"Ticket #{ticket_id} marked as resolved.")
                    st.rerun()

    st.markdown("---")

if __name__ == "__main__":
    agent_dashboard()