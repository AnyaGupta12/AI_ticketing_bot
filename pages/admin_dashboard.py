# import streamlit as st
# import sqlite3
# import fitz  # PyMuPDF

# # --- Database Connection ---
# @st.cache_resource
# def get_connection():
#     conn = sqlite3.connect("app.db", check_same_thread=False)
#     conn.execute("PRAGMA foreign_keys = ON;")
#     return conn

# # --- Function to extract text from PDF bytes ---
# def extract_text_from_pdf(pdf_bytes):
#     text = ""
#     try:
#         doc = fitz.open(stream=pdf_bytes, filetype="pdf")
#         for page in doc:
#             text += page.get_text()
#     except Exception as e:
#         st.error(f"Error extracting text from PDF: {e}")
#     return text

# # --- Admin Dashboard Page ---
# def admin_dashboard():
#     company_id = st.session_state.get("company_id")
#     if not company_id:
#         st.error("Unauthorized access. Please log in.")
#         st.stop()
#     st.subheader(f"Admin Dashboard - Welcome {st.session_state.get('user_name', '')}")
#     st.markdown("Upload documents to your company's Knowledge Base.")
#     st.divider()

#     # Upload PDF file
#     uploaded_file = st.file_uploader("Upload a PDF file (optional)", type=["pdf"])

#  # ...existing code...

#     with st.form("upload_form", clear_on_submit=True):
#         title = company_id

#         # If PDF uploaded, extract text and show in textarea
#         if uploaded_file is not None:
#             pdf_bytes = uploaded_file.read()
#             extracted_text = extract_text_from_pdf(pdf_bytes)
#         else:
#             extracted_text = ""

#         # Ensure extracted_text is a string
#         extracted_text = str(extracted_text)

#         content = st.text_area("Document Content", height=200, value=extracted_text)
        
#         submitted = st.form_submit_button("📤 Upload to KB")

#         if submitted:
#             if not str(content).strip():
#                 st.error("Please fill in both title and content.")
#             else:
#                 try:
#                     conn = get_connection()
#                     c = conn.cursor()
#                     c.execute(
#                         "INSERT INTO KBDocument (company_id, title, content) VALUES (?, ?, ?)",
#                         (st.session_state["company_id"], str(title).strip(), str(content).strip())
#                     )
#                     conn.commit()
#                     st.success("✅ Document uploaded successfully to Knowledge Base!")
#                 except sqlite3.Error as e:
#                     st.error(f"Database error: {e}")
# # ...existing code...


# import streamlit as st
# from db import execute
# import pandas as pd

# if "role" not in st.session_state or st.session_state["role"] != "admin":
#     st.error("Access denied. Admins only.")
#     st.stop()

# def get_all_tickets(company_id):
#     cur = execute("""
#         SELECT T.id, U.name AS submitted_by, T.product, T.problem_description,
#                T.priority, T.status, T.created_at
#         FROM Tickets T
#         LEFT JOIN User U ON T.user_id = U.id
#         WHERE T.company_id = ?
#         ORDER BY T.created_at DESC
#     """, (company_id,))
#     return cur.fetchall()

# def get_agents(company_id):
#     cur = execute("SELECT id, name FROM User WHERE company_id = ? AND role = 'agent'", (company_id,))
#     return cur.fetchall()

# st.title("Admin Dashboard")

# if "role" not in st.session_state or st.session_state["role"] != "admin":
#     st.error("Access denied. Admins only.")
#     st.stop()

# company_id = st.session_state["company_id"]

# # Show Tickets
# st.header("All Tickets")
# tickets = get_all_tickets(company_id)
# df = pd.DataFrame(tickets, columns=["ID", "Submitted By", "Product", "Description", "Priority", "Status", "Created At"])
# st.dataframe(df, use_container_width=True)

# # Assign Ticket
# st.subheader("Assign Ticket to Agent")
# ticket_id = st.text_input("Enter Ticket ID")
# agents = get_agents(company_id)
# agent_map = {f"{name} (ID {id})": id for id, name in agents}
# agent_choice = st.selectbox("Assign to", list(agent_map.keys()))

# if st.button("Assign"):
#     agent_id = agent_map[agent_choice]
#     execute("UPDATE Tickets SET user_id = ? WHERE id = ? AND company_id = ?", (agent_id, ticket_id, company_id))
#     st.success(f"Ticket {ticket_id} assigned to agent.")

# # View KB Docs
# st.subheader("Knowledge Base Documents")
# kb_cur = execute("SELECT title, content FROM KBDocument WHERE company_id = ?", (company_id,))
# kbs = kb_cur.fetchall()
# for title, content in kbs:
#     with st.expander(title):
#         st.markdown(content)


# admin_dashboard.py
import streamlit as st
from pages.session_utils import require_role
import sqlite3
import fitz  # PyMuPDF

require_role("admin")

@st.cache_resource
def get_connection():
    conn = sqlite3.connect("app.db", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def extract_text_from_pdf(pdf_bytes):
    text = ""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text()
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
    return text

def admin_dashboard():
    st.subheader(f"Admin Dashboard - Welcome {st.session_state['user_name']}")
    st.markdown("Upload documents to your company's Knowledge Base.")
    st.divider()

    uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

    with st.form("upload_form", clear_on_submit=True):
        if uploaded_file is not None:
            pdf_bytes = uploaded_file.read()
            extracted_text = extract_text_from_pdf(pdf_bytes)
        else:
            extracted_text = ""

        content = st.text_area("Document Content", height=200, value=extracted_text)
        submitted = st.form_submit_button("📤 Upload to KB")

        if submitted:
            if not content.strip():
                st.error("Please enter document content.")
            else:
                conn = get_connection()
                c = conn.cursor()
                c.execute(
                    "INSERT INTO KBDocument (company_id, title, content) VALUES (?, ?, ?)",
                    (st.session_state["company_id"], "Uploaded KB Doc", content.strip())
                )
                conn.commit()
                st.success("✅ Document uploaded to Knowledge Base!")
