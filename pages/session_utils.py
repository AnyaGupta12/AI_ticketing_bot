# session_utils.py
import streamlit as st

def require_login():
    if "user_id" not in st.session_state or "role" not in st.session_state:
        st.warning("Access denied. Please log in.")
        st.stop()

def require_role(required_role):
    require_login()
    if st.session_state["role"] != required_role:
        st.warning(f"Access denied. {required_role.capitalize()}s only.")
        st.stop()
