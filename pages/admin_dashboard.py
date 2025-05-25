import streamlit as st
import sqlite3
import fitz  # PyMuPDF
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
# --- Database Connection ---
@st.cache_resource
def get_connection():
    conn = sqlite3.connect("app.db", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# --- Function to extract text from PDF bytes ---
def extract_text_from_pdf(pdf_bytes):
    text = ""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text()
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
    return text


def get_agents_with_ticket_count(company_id):
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute("""
        SELECT U.id, U.name, U.email, COUNT(T.id) as resolved_count
        FROM User U
        LEFT JOIN Tickets T ON U.id = T.user_id AND T.status = 'Closed'
        WHERE U.role = 'agent' AND U.company_id = ?
        GROUP BY U.id;
    """, (company_id,))
    return c.fetchall()

def delete_agent(agent_id):
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute("DELETE FROM User WHERE id = ? AND role = 'agent'", (agent_id,))
    conn.commit()
    conn.close()


# --- Admin Dashboard Page ---
def admin_dashboard():
    company_id = st.session_state.get("company_id")
    if not company_id:
        st.error("Unauthorized access. Please log in.")
        st.stop()

    st.subheader(f"Admin Dashboard - Welcome {st.session_state.get('user_name', '')}")

    # === Ticket Stats ===
    conn = get_connection()
    c = conn.cursor()

    # Fetch ticket status count
    c.execute("SELECT status, COUNT(*) FROM Tickets WHERE company_id = ? GROUP BY status;", (company_id,))
    status_data = c.fetchall()
    ticket_df = pd.DataFrame(status_data, columns=["Status", "Count"])

        # Bar chart

    st.markdown("### Ticket Status Overview")

    if not ticket_df.empty:
        plt.style.use("dark_background")

        fig, ax = plt.subplots(figsize=(4, 4), dpi=100)  # 4 inches * 100 dpi = 400 pixels

        # Data
        labels = ticket_df["Status"]
        sizes = ticket_df["Count"]
        colors = ["#FFA07A", "#90EE90", "#6495ED"]  # open, closed, handoff

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors[:len(labels)],
            autopct='%1.1f%%',
            startangle=140,
            textprops={'color': "white", 'fontsize': 8},
            wedgeprops={'linewidth': 0.5, 'edgecolor': 'gray'}
        )

        ax.set_title("Ticket Status", color='white', fontsize=10)
        fig.tight_layout()

        # Save figure to a bytes buffer
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches='tight', transparent=True)
        plt.close(fig)  # Close the figure to free memory
        buf.seek(0)

        # Display image with HTML style for size control
        st.markdown(
            """
            <div style="width: 400px; height: 400px; margin: auto;">
                <img src="data:image/png;base64,{}" style="width: 400px; height: 400px; display: block; margin-left: auto; margin-right: auto;">
            </div>
            """.format(base64.b64encode(buf.read()).decode()),
            unsafe_allow_html=True
        )

    else:
        st.info("No tickets found.")




    # === User Stats ===
    c.execute("SELECT role, COUNT(*) FROM User WHERE company_id = ? GROUP BY role;", (company_id,))
    role_data = c.fetchall()
    role_df = pd.DataFrame(role_data, columns=["Role", "Count"])

    st.markdown("### Users and Agents")
    st.dataframe(role_df)

    st.subheader("Agents and Resolved Tickets")

    agents = get_agents_with_ticket_count(company_id)

    for agent_id, name, email, count in agents:
        col1, col2, col3, col4 = st.columns([3, 3, 2, 2])
        col1.write(f"**Name:** {name}")
        col2.write(f"**Email:** {email}")
        col3.write(f"✅ Resolved:** {count}")
        if col4.button("❌ Delete", key=f"delete_{agent_id}"):
            delete_agent(agent_id)
            st.success(f"Deleted agent {name}")
            st.rerun()


    st.divider()
    st.markdown("### Knowledge Base Upload")

    st.markdown("Upload documents to your company's Knowledge Base.")
    st.divider()

    # Upload PDF file
    uploaded_file = st.file_uploader("Upload a PDF file (optional)", type=["pdf"])

 # ...existing code...

    with st.form("upload_form", clear_on_submit=True):
        title = company_id

        # If PDF uploaded, extract text and show in textarea
        if uploaded_file is not None:
            pdf_bytes = uploaded_file.read()
            extracted_text = extract_text_from_pdf(pdf_bytes)
        else:
            extracted_text = ""

        # Ensure extracted_text is a string
        extracted_text = str(extracted_text)

        content = st.text_area("Document Content", height=200, value=extracted_text)
        
        submitted = st.form_submit_button(" Upload to KB")

        if submitted:
            if not str(content).strip():
                st.error("Please fill in both title and content.")
            else:
                try:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute(
                        "INSERT INTO KBDocument (company_id, title, content) VALUES (?, ?, ?)",
                        (st.session_state["company_id"], str(title).strip(), str(content).strip())
                    )
                    conn.commit()
                    st.success(" Document uploaded successfully to Knowledge Base!")
                except sqlite3.Error as e:
                    st.error(f"Database error: {e}")
# ...existing code...