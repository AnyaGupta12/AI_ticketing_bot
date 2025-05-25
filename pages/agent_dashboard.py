# # File: agent_dashboard.py
import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import pandas as pd
from db import get_conn



def agent_dashboard():

    st.markdown(
    f"<h2 style='text-align: center;'>Agent Dashboard ({st.session_state['user_name']})</h2>",
    unsafe_allow_html=True
)

    agent_id = st.session_state.get("user_id")
    company_id = st.session_state.get("company_id")
    agent_id = st.session_state.get("user_id")
    conn = sqlite3.connect("app.db", check_same_thread=False)
    c = conn.cursor()

    # Load all open tickets
    c.execute("""
        SELECT id, product, priority, problem_description, contact_name, contact_email
        FROM Tickets
        WHERE company_id = ? AND status = 'Handoff'
        ORDER BY created_at DESC;
    """, (company_id,))
    tickets = c.fetchall()

    if not tickets:
        st.success("No handoff tickets at the moment.")
        return
    
    if "user_id" not in st.session_state or "user_name" not in st.session_state:
        st.error("Please log in to access the agent dashboard.")
        st.stop()

    st.markdown("### Handoff Tickets")

    for ticket in tickets:
        ticket_id, product, priority, desc, contact_name, contact_email = ticket
        with st.expander(f"Ticket #{ticket_id} - {product} [{priority}]"):
            st.warning("This ticket was flagged by the AI for human attention.")
            st.write(f"**Submitted by:** {contact_name} ({contact_email})")
            st.write(f"**Issue:** {desc}")

            if st.button(f"Join Chat", key=f"join_{ticket_id}"):
                st.session_state['current_ticket_id'] = ticket_id
                st.switch_page("pages/agent_chat.py")  # or use st.experimental_set_query_params

            if st.button(f" Mark as Resolved", key=f"resolve_{ticket_id}"):
                c.execute("""
                UPDATE Tickets SET status = 'closed', user_id = ? WHERE id = ?""", (agent_id, ticket_id))
                conn.commit()
                st.success(f"Ticket #{ticket_id} marked as resolved.")
                st.rerun()

    st.markdown("---")

if __name__ == "__main__":
    agent_dashboard()