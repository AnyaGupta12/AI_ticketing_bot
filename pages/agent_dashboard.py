# # File: agent_dashboard.py
import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import pandas as pd
from db import get_conn

def agent_dashboard():

    st.subheader(f" Agent Dashboard ({st.session_state['user_name']})")
    st.markdown("*(Here you’ll eventually see your ticket queue and AI-assist tools.)*")

    agent_id = st.session_state.get("user_id")
    company_id = st.session_state.get("company_id")
    agent_id = st.session_state.get("user_id")
    conn = sqlite3.connect("app.db", check_same_thread=False)
    c = conn.cursor()

    # -- Ticket Summary for this agent
    c.execute("""
        SELECT status, COUNT(*) FROM Tickets
        WHERE user_id = ? AND company_id = ?
        GROUP BY status;
    """, (agent_id, company_id))
    rows = c.fetchall()

    if rows:
        st.markdown("### Your Ticket Summary")
        df = pd.DataFrame(rows, columns=["Status", "Count"])
        fig, ax = plt.subplots()
        ax.pie(df["Count"], labels=df["Status"], autopct="%1.1f%%", startangle=90, colors=["orange", "green"])
        ax.axis("equal")
        st.pyplot(fig)
    else:
        st.info("You have not handled any tickets yet.")

    # Load all open tickets
    c.execute("""
        SELECT id, product, priority, problem_description, contact_name, contact_email
        FROM Tickets
        WHERE company_id = ? AND status = 'Open'
        ORDER BY created_at DESC;
    """, (company_id,))
    tickets = c.fetchall()

    if not tickets:
        st.success("No open tickets at the moment.")
        return

    st.markdown("### Open Tickets")

    for ticket in tickets:
        ticket_id, product, priority, desc, contact_name, contact_email = ticket
        with st.expander(f"Ticket #{ticket_id} - {product} [{priority}]"):
            st.write(f"**Submitted by:** {contact_name} ({contact_email})")
            st.write(f"**Issue:** {desc}")

            if st.button(f" Mark as Resolved", key=f"resolve_{ticket_id}"):
                c.execute("UPDATE Tickets SET status = 'Closed' WHERE id = ?", (ticket_id,))
                conn.commit()
                st.success(f"Ticket #{ticket_id} marked as resolved.")
                st.rerun()

    st.markdown("---")
    st.markdown("### Check Company Knowledge Base")

    query = st.text_input("Enter your question to the knowledge base")
    if st.button("Ask"):
        if query:
            from pages.chatbot_utils import query_kb
            response = query_kb(query, company_id)
            st.success(response)
        else:
            st.warning("Please enter a question.")