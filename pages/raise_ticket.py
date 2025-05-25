import streamlit as st
import sqlite3
from datetime import datetime
import uuid
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
import sqlite3

def send_ticket_email(to_email, contact_name, ticket_id, product, description, priority):
    msg = EmailMessage()
    msg['Subject'] = f"Support Ticket #{ticket_id} Created"
    msg['From'] = "cs24mtech11025@iith.ac.in"        # Replace with your email
    msg['To'] = to_email

    body = f"""
Hi {contact_name},

Your support ticket has been successfully created. Here are the details:

Ticket ID: {ticket_id}
Product: {product}
Priority: {priority}
Description:
{description}

Our support team will reach out to you shortly.

Thank you,
Hack_X Support Team
    """.strip()

    msg.set_content(body)

    try:
        # Login and send email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login("hackx.tickets@gmail.com", "wqzi rpso vcte fyei")  # Use App Password if 2FA is on
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"⚠️ Failed to send confirmation email: {e}")
        return False

def check_inactivity_and_close(session_id, ticket_id):
    conn = sqlite3.connect("app.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        SELECT MAX(timestamp) FROM chat_sessions
        WHERE session_id = ? AND sender = 'user'
    """, (session_id,))
    last_user_time = c.fetchone()[0]

    if last_user_time:
        last_time = datetime.strptime(last_user_time, "%Y-%m-%d %H:%M:%S.%f")
        if datetime.now() - last_time > timedelta(minutes=30):
            c.execute("UPDATE Tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
            conn.commit()
            st.warning("⚠️ No activity for 30 minutes. Ticket is now closed.")
            return True
    return False

def find_session_by_ticket(ticket_id):
    """
    Returns the most recent session_id for this ticket_id
    where the last message is within 30 minutes, else None.
    """
    conn = sqlite3.connect("app.db", check_same_thread=False)
    c    = conn.cursor()
    cutoff = datetime.now() - timedelta(minutes=30)

    c.execute("""
        SELECT DISTINCT session_id
          FROM chat_sessions
         WHERE ticket_id = ?
           AND timestamp >= ?
         ORDER BY timestamp DESC
         LIMIT 1
    """, (ticket_id, cutoff))

    row = c.fetchone()
    return row[0] if row else None


def save_chat_message(session_id, sender, message, ticket_id=None):
    conn = sqlite3.connect("app.db", check_same_thread=False)
    c = conn.cursor()

    # Fetch user_name from Tickets table using ticket_id
    if ticket_id:
        c.execute("SELECT contact_name FROM Tickets WHERE id = ?", (ticket_id,))
        result = c.fetchone()
        user_name = result[0] if result else "Unknown"
    else:
        user_name = "Unknown"

    # Save the message to chat_sessions table
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

    # --- Resume Chat UI (by Ticket ID) ---
    st.subheader("🔁 Resume Previous Chat")

    ticket_input = st.text_input("Enter your Ticket # to resume:", max_chars=10)
    resume_btn   = st.button("Resume Chat")

    if resume_btn:
        if not ticket_input.isdigit():
            st.error("Please enter a valid numeric ticket ID.")
        else:
            ticket_id = int(ticket_input)
            session_id = find_session_by_ticket(ticket_id)   # your helper
            if session_id:
                st.session_state["ticket_id"]  = ticket_id
                st.session_state["session_id"] = session_id
                st.success(f"Resuming chat for Ticket #{ticket_id}…")
                st.switch_page("pages/chatbot.py")
            else:
                st.error("No active session found for that ticket (or it expired).")

    st.markdown("---")

    # --- Create a New Ticket ---
    st.subheader("📩 Create a New Ticket")
    # … the rest of your form logic follows here …


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

            send_ticket_email(
                to_email=contact_email,
                contact_name=contact_name,
                ticket_id=ticket_id,
                product=product,
                description=problem_description,
                priority=priority
            )

            st.switch_page("pages/chatbot.py")
            st.rerun()

        except sqlite3.Error as e:
            st.error(f"Database error: {e}")

if __name__ == "__main__":
    raise_ticket()