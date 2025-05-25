# import streamlit as st
# import sqlite3
# from passlib.context import CryptContext

# # --- Password hashing context ---
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# # --- Database connection ---
# @st.cache_resource
# def get_connection():
#     conn = sqlite3.connect("app.db", check_same_thread=False)
#     conn.execute("PRAGMA foreign_keys = ON;")
#     return conn

# # --- CSS Styling ---
# def local_css():
#     st.markdown(
#         """
#         <style>
#         /* Increase font size of input labels and inputs */
#         div.stTextInput > label, div.stTextInput > div > input {
#             font-size: 20px !important;
#         }
#         /* Center and enlarge the submit button */
#         div.stButton > button {
#             display: block;
#             margin: 20px auto 0 auto;
#             padding: 10px 40px;
#             font-size: 20px;
#         }
#         </style>
#         """,
#         unsafe_allow_html=True,
#     )

# # --- Login Page ---
# def login_page():
#     local_css()  # Apply custom CSS styles
#     st.subheader("Agent / Admin Login")

#     with st.form("login_form"):
#         email = st.text_input("Email", placeholder="Enter your email")
#         password = st.text_input("Password", type="password", placeholder="Enter your password")
#         login_submit = st.form_submit_button("Login")

#     if login_submit:
#         if not email or not password:
#             st.error("Please fill in all fields.")
#             return

#         conn = get_connection()
#         c = conn.cursor()

#         try:
#             c.execute("SELECT id, company_id, name, password_hash, role FROM User WHERE email = ?;", (email,))
#             user = c.fetchone()
#         except sqlite3.Error as e:
#             st.error(f"Database error: {e}")
#             return

#         if user and pwd_context.verify(password, user[3]):
#             st.session_state['user_id'] = user[0]
#             st.session_state['company_id'] = user[1]
#             st.session_state['user_name'] = user[2]
#             st.session_state['role'] = user[4]

#             # Redirect to dashboard page based on role
#             if user[4] == "admin":
#                 st.session_state.page = "Admin Dashboard"
#             else:
#                 st.session_state.page = "Agent Dashboard"

#             st.success(f"✅ Logged in as {user[2]} ({user[4]})")
#             st.rerun()  # Triggers rerun to update page
#         else:
#             st.error("❌ Invalid email or password.")



# login.py
import streamlit as st
import sqlite3
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@st.cache_resource
def get_connection():
    conn = sqlite3.connect("app.db", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def login_page():
    st.subheader("Agent / Admin Login")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        login_submit = st.form_submit_button("Login")

    if login_submit:
        if not email or not password:
            st.error("Please fill in all fields.")
            return

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, company_id, name, password_hash, role FROM User WHERE email = ?", (email,))
        user = c.fetchone()

        if user and pwd_context.verify(password, user[3]):
            st.session_state['user_id'] = user[0]
            st.session_state['company_id'] = user[1]
            st.session_state['user_name'] = user[2]
            st.session_state['role'] = user[4]
            st.session_state['page'] = "Dashboard"
            st.success(f"✅ Logged in as {user[2]} ({user[4]})")
            st.rerun()
        else:
            st.error("❌ Invalid email or password.")
