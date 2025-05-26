# File: app.py
import streamlit as st
from db import init_db
from pages.registration import register_company, register_agent
from pages.login import login_page
from pages.admin_dashboard import admin_dashboard
from pages.agent_dashboard import agent_dashboard
from pages.raise_ticket import raise_ticket



st.set_page_config(page_title="Hack_X Support", layout="wide")

# Inject custom CSS
st.markdown("""
    <style>
        .card {
            background-color: #fff;
            border-radius: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            padding: 20px;
            text-align: center;
            width: 100%;
            height: 100%;
        }

        .card img {
            width: 100%;
            height: 400px;
            max-width: 300px;
            object-fit: cover;
            border-radius: 10px;
        }

        .card-title {
            font-size: 22px;
            font-weight: bold;
            color: black;  /* <--- This ensures the title shows up */
            margin: 15px 0 10px;
        }

        .card-button {
            background-color: #4B8BBE;
            color: white;
            padding: 10px 20px;
            font-size: 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }

        .card-button:hover {
            background-color: #306998;
        }
            
        .title {
            text-align: center;
            font-size: 36px;
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 30px;
            color: #4B8BBE;
        }
        div.stButton > button {
            background-color: #4CAF50;
            color: white;
            border-radius: 8px;
            padding: 10px 0;
            font-size: 16px;
            width: 100%;
            cursor: pointer;
            border: none;
            transition: background-color 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #45a049;
        }

    </style>
""", unsafe_allow_html=True)

# Title
st.markdown("<div class='title'>Welcome to Hack_X Support Platform</div>", unsafe_allow_html=True)

# Role Cards
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
        <div class='card'>
            <img src='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTATN4AJS6gxKxnnK3-IYjI0X2kKucQ_Ml2ow&s' />
            <div class='card-title'>User</div>
        </div>
    """, unsafe_allow_html=True)

     # Use st.button styled with same class using st.markdown workaround
    if st.button("Raise Ticket", key="raise_ticket"):
        st.session_state.page = "Raise Ticket"
        st.rerun()

with col2:
    st.markdown("""
        <div class='card'>
            <img src='https://i.pinimg.com/736x/ee/4e/21/ee4e21e3020017aac4130f989f1e516c.jpg' style="width:100%; height:auto; border-radius: 8px;" />
            <div class='card-title' style="color:black; font-weight:bold; text-align:center; margin-top:10px;">Company</div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("Enter Portal", key="company_portal"):
        st.session_state.page = "Portal"
        st.rerun()


with col3:
    st.markdown("""
        <div class='card'>
            <img src='data:image/jpeg;base64,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' />
            <div class='card-title'>Agent</div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("Enter Portal", key="agent_portal"):
        st.session_state.page = "Portal"
        st.rerun()

def main():
    if "page" not in st.session_state:
        st.session_state.page = "Home"  # Or whatever your default page is
    elif st.session_state.page == "Raise Ticket":
        st.switch_page("pages/raise_ticket.py")
        st.rerun()  # Redirect to the raise ticket page
    elif st.session_state.page == "Portal":
        st.switch_page("pages/portal.py")  # Your other page function
    else:
        st.switch_page("pages/portal.py")

if __name__ == "__main__":
    main()