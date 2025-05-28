# File: agent_dashboard.py
import streamlit as st

def agent_dashboard():
    st.subheader(f"🧑‍💼 Agent Dashboard ({st.session_state['user_name']})")
    st.markdown("*(Here you’ll eventually see your ticket queue and AI-assist tools.)*")
