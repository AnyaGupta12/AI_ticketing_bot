# # File: agent_dashboard.py
# import streamlit as st

# def agent_dashboard():
#     st.subheader(f"🧑‍💼 Agent Dashboard ({st.session_state['user_name']})")
#     st.markdown("*(Here you’ll eventually see your ticket queue and AI-assist tools.)*")

# agent_dashboard.py
import streamlit as st
from pages.session_utils import require_role

require_role("agent")

def agent_dashboard():
    st.subheader(f"Agent Dashboard - Welcome {st.session_state['user_name']}")
    st.markdown("Agent tools will go here.")


# import streamlit as st
# from db import execute
# import pandas as pd

# # Access Control
# if "role" not in st.session_state or st.session_state["role"] != "agent":
#     st.error("Access denied. Agents only.")
#     st.stop()

# def get_my_tickets(agent_id):
#     cur = execute("""
#         SELECT id, product, problem_description, priority, status, created_at
#         FROM Tickets
#         WHERE user_id = ?
#         ORDER BY created_at DESC
#     """, (agent_id,))
#     return cur.fetchall()

# def update_ticket_status(ticket_id, new_status):
#     execute("UPDATE Tickets SET status = ? WHERE id = ?", (new_status, ticket_id))

# st.title("Agent Dashboard")

# if "role" not in st.session_state or st.session_state["role"] != "agent":
#     st.error("Access denied. Agents only.")
#     st.stop()

# agent_id = st.session_state["user_id"]

# # Show My Tickets
# st.header("My Assigned Tickets")
# tickets = get_my_tickets(agent_id)
# df = pd.DataFrame(tickets, columns=["ID", "Product", "Description", "Priority", "Status", "Created At"])
# st.dataframe(df, use_container_width=True)

# # Update Status
# st.subheader("Update Ticket Status")
# ticket_id = st.text_input("Enter Ticket ID")
# new_status = st.selectbox("New Status", ["Open", "In Progress", "Resolved", "Closed"])
# if st.button("Update Status"):
#     update_ticket_status(ticket_id, new_status)
#     st.success(f"Ticket {ticket_id} updated to {new_status}")

# # View KB Docs
# st.subheader("Company KB")
# kb_cur = execute("SELECT title, content FROM KBDocument WHERE company_id = ?", (st.session_state["company_id"],))
# kbs = kb_cur.fetchall()
# for title, content in kbs:
#     with st.expander(title):
#         st.markdown(content)
