# File: pages/agent_chat.py
import streamlit as st
import sqlite3
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# Auto-refresh every 10 seconds
st_autorefresh(interval=15000, limit=None, key="chat_refresh")

def get_cutoff(minutes: int) -> datetime:
    return datetime.now() - timedelta(minutes=minutes)

def get_conn():
    return sqlite3.connect("app.db", check_same_thread=False)

def agent_chat_page():
    st.title(f"🛠️ Agent Chat – Ticket #{st.session_state.get('current_ticket_id')}")
    ticket_id = st.session_state.get("current_ticket_id")
    if not ticket_id:
        st.error("No ticket selected. Go back to the dashboard.")
        st.stop()

    conn = get_conn()
    c = conn.cursor()

    # 1. Load last 30 minutes of chat
    cutoff = get_cutoff(30)
    c.execute(
        """
        SELECT sender, message, timestamp
          FROM chat_sessions
         WHERE ticket_id = ?
           AND timestamp >= ?
         ORDER BY timestamp
        """,
        (ticket_id, cutoff)
    )
    rows = c.fetchall()

    if not rows:
        st.warning("No chat history in the last 30 minutes.")
    else:
        for sender, message, _ in rows:
            role = "user" if sender == "user" else "assistant"
            with st.chat_message(role):
                st.write(message)

    # 2. Agent input
    agent_input = st.chat_input("Your response…")
    if agent_input:
        c.execute(
            """
            INSERT INTO chat_sessions 
              (session_id, user_name, sender, message, timestamp, ticket_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "agent-session",                  # Dummy session_id
                st.session_state["user_name"],    # agent name
                "agent",
                agent_input,
                datetime.now(),
                ticket_id
            )
        )
        conn.commit()
        with st.chat_message("assistant"):
            st.write(agent_input)
        st.rerun()

    # 3. Close ticket
    # 3. Close ticket
    if st.button("✅ Mark Ticket Closed"):
        c.execute(
            """
            UPDATE Tickets
               SET status = 'Closed', user_id = ?
             WHERE id = ?
            """,
            (st.session_state["user_id"], ticket_id)
        )
        conn.commit()
        st.success("Ticket closed.")

        # Optional: Clear current ticket but keep user login info
        del st.session_state["current_ticket_id"]

        # Redirect to dashboard (user_id and user_name are still intact)
        st.switch_page("pages/agent_dashboard.py")

if __name__ == "__main__":
    agent_chat_page()
