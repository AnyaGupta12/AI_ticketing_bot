# registration.py

import streamlit as st
import sqlite3
from passlib.context import CryptContext

# --- Password Hashing Context ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password):
    return pwd_context.hash(password)

# --- Reuse SQLite connection ---
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('app.db', check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# --- Company Registration ---
def register_company():
    st.subheader("🏢 Company Registration")
    with st.form("company_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("Company Name", max_chars=50)
            admin_name = st.text_input("Admin Full Name")
        with col2:
            admin_email = st.text_input("Admin Email")
            admin_password = st.text_input("Admin Password", type="password")

        submitted = st.form_submit_button("Register Company")

    if submitted:
        if not all([company_name, admin_name, admin_email, admin_password]):
            st.error("All fields are required.")
            return

        conn = get_connection()
        c = conn.cursor()

        try:
            # Insert company
            c.execute("INSERT INTO Company (name) VALUES (?);", (company_name,))
            company_id = c.lastrowid

            # Hash password
            pw_hash = hash_password(admin_password)

            # Insert admin user
            c.execute(
                "INSERT INTO User (company_id, name, email, password_hash, role) VALUES (?, ?, ?, ?, ?);",
                (company_id, admin_name, admin_email, pw_hash, 'admin')
            )
            conn.commit()
            st.session_state["company_id"] = company_id
            st.success(f"✅ Company '{company_name}' registered successfully with admin '{admin_name}'!")
        except sqlite3.IntegrityError:
            st.error("⚠️ Company name or admin email already exists.")

# --- Agent Registration ---
def register_agent():
    st.subheader("👤 Agent Registration")
    conn = get_connection()
    c = conn.cursor()

    # Get list of companies
    companies = [row[0] for row in c.execute("SELECT name FROM Company ORDER BY name;").fetchall()]
    if not companies:
        st.warning("⚠️ No companies found. Register a company first.")
        return

    with st.form("agent_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            selected_company = st.selectbox("Select Company", companies)
            agent_name = st.text_input("Agent Full Name")
        with col2:
            agent_email = st.text_input("Agent Email")
            agent_password = st.text_input("Agent Password", type="password")

        submitted = st.form_submit_button("Register Agent")

    if submitted:
        if not all([selected_company, agent_name, agent_email, agent_password]):
            st.error("All fields are required.")
            return

        # Find company_id
        c.execute("SELECT id FROM Company WHERE name = ?;", (selected_company,))
        row = c.fetchone()
        if not row:
            st.error("Company not found.")
            return
        company_id = row[0]

        try:
            pw_hash = hash_password(agent_password)
            c.execute(
                "INSERT INTO User (company_id, name, email, password_hash, role) VALUES (?, ?, ?, ?, ?);",
                (company_id, agent_name, agent_email, pw_hash, 'agent')
            )
            conn.commit()
            st.success(f"✅ Agent '{agent_name}' registered under '{selected_company}'!")
        except sqlite3.IntegrityError:
            st.error("⚠️ Agent email already exists.")
