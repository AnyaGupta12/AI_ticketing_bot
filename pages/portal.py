# File: app.py
import streamlit as st
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db import init_db
from pages.registration import register_company, register_agent
from pages.login import login_page
from pages.admin_dashboard import admin_dashboard
from pages.agent_dashboard import agent_dashboard


def portal_page():
    init_db()

    # Set default page
    if "page" not in st.session_state:
        st.session_state.page = "Login"

    # --- Navigation Buttons (TOP NAVBAR) ---
    if "role" not in st.session_state:
        col1, col2, col3, col4 = st.columns([1,1,1,1])  # equal width columns
        with col1:
            if st.button("Register Company"):
                st.session_state.page = "Register Company"
        with col2:
            if st.button("Register Agent"):
                st.session_state.page = "Register Agent"
        with col3:
            if st.button("Login"):
                st.session_state.page = "Login"
        with col4:
            if st.button("Raise Ticket"):
                st.session_state.page = "Raise Ticket"
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.session_state["role"] == "admin":
                if st.button("Admin Dashboard"):
                    st.session_state.page = "Admin Dashboard"
            else:
                if st.button("Agent Dashboard"):
                    st.session_state.page = "Agent Dashboard"
        with col2:
            if st.button("Raise Ticket"):
                st.session_state.page = "Raise Ticket"
        with col3:
            if st.button("Logout"):
                for key in ['user_id', 'company_id', 'user_name', 'role', 'page']:
                    st.session_state.pop(key, None)
                st.success("🔓 Logged out")
                st.rerun()

    # --- Title Centered (AFTER NAVBAR) ---
    st.markdown(
        "<h1 style='text-align: center;'> Hack_X Ticketing Platform</h1>",
        unsafe_allow_html=True
    )

    st.markdown("---")

    # --- Route to current page ---
    page = st.session_state.page
    if page == "Register Company":
        register_company()
    elif page == "Register Agent":
        register_agent()
    elif page == "Login":
        login_page()
    elif page == "Admin Dashboard":
        admin_dashboard()
    elif page == "Agent Dashboard":
        agent_dashboard()
    elif page == "Raise Ticket":
        st.switch_page("pages/raise_ticket.py")
    elif page == "Chatbot":
        st.switch_page("pages/chatbot.py")

if __name__ == "__main__":
    portal_page()
    st.markdown("---")
    st.markdown("Made with ❤️ by Hack_X Team")
