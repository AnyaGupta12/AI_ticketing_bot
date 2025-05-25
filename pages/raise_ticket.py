import streamlit as st
import sqlite3
from datetime import datetime
import uuid

def save_chat_message(session_id, user_name, sender, message, ticket_id=None):
    conn = sqlite3.connect("app.db", check_same_thread=False)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO chat_sessions (session_id, user_name, sender, message, timestamp, ticket_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session_id, user_name, sender, message, datetime.now(), ticket_id)
    )
    conn.commit()

from datetime import datetime, timedelta

def load_recent_chat(session_id):
    conn = sqlite3.connect("app.db", check_same_thread=False)
    c = conn.cursor()
    cutoff = datetime.now() - timedelta(minutes=30)
    c.execute(
        """
        SELECT sender, message FROM chat_sessions
        WHERE session_id = ? AND timestamp >= ?
        ORDER BY timestamp
        """,
        (session_id, cutoff)
    )
    return c.fetchall()


@st.cache_resource
def get_connection():
    conn = sqlite3.connect("app.db", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def raise_ticket():
    st.title("📝 Raise a Support Ticket")

    conn = get_connection()
    c = conn.cursor()

    # --- Resume Chat UI ---
    st.subheader("🔁 Resume Previous Chat")
    user_name = st.text_input("Enter your name to resume your chat session:")

    if user_name:
        session_id = f"{user_name}_{str(uuid.uuid4())[:8]}"
        st.session_state["user_name"] = user_name
        st.session_state["session_id"] = session_id
        st.switch_page("pages/chatbot.py")
        st.rerun()

    st.markdown("---")
    st.subheader("📩 Create a New Ticket")

    # --- Get list of companies for dropdown ---
    c.execute("SELECT id, name FROM Company")
    companies = c.fetchall()
    company_options = {name: cid for cid, name in companies}

    # --- Ticket Form ---
    with st.form("ticket_form"):
        contact_name = st.text_input("Your Name", max_chars=100)
        company_name = st.selectbox("Select Your Company", list(company_options.keys()))
        product = st.text_input("Product Name", max_chars=100)
        problem_description = st.text_area("Problem Description", height=150)
        priority = st.selectbox("Priority", ["Low", "Medium", "High", "Critical"])
        contact_email = st.text_input("Contact Email", max_chars=100)

        submit = st.form_submit_button("Submit Ticket")

    if submit:
        if not (company_name and product and problem_description and contact_email and contact_name):
            st.error("Please fill all required fields.")
            return

        company_id = company_options[company_name]
        user_id = None  # anonymous

        try:
            # Insert ticket
            c.execute(
                """
                INSERT INTO Tickets (user_id, company_id, product, problem_description, priority, contact_email, contact_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, company_id, product, problem_description, priority, contact_email, contact_name)
            )
            ticket_id = c.lastrowid
            conn.commit()

            # Create session ID
            session_id = f"{contact_name}_{str(uuid.uuid4())[:8]}"

            # Store session details
            st.session_state["ticket_id"] = ticket_id
            st.session_state["user_name"] = contact_name
            st.session_state["session_id"] = session_id
            st.session_state["page"] = "Chatbot"

            st.success("Ticket submitted! Redirecting to chatbot...")
            st.switch_page("pages/chatbot.py")
            st.rerun()

        except sqlite3.Error as e:
            st.error(f"Database error: {e}")
            
if __name__ == "__main__":
    raise_ticket()