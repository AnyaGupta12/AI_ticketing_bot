import streamlit as st
import sqlite3
import fitz  # PyMuPDF

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

# --- Admin Dashboard Page ---
def admin_dashboard():
    company_id = st.session_state.get("company_id")
    if not company_id:
        st.error("Unauthorized access. Please log in.")
        st.stop()
    st.subheader(f"Admin Dashboard - Welcome {st.session_state.get('user_name', '')}")
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
        
        submitted = st.form_submit_button("📤 Upload to KB")

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
                    st.success("✅ Document uploaded successfully to Knowledge Base!")
                except sqlite3.Error as e:
                    st.error(f"Database error: {e}")
# ...existing code...