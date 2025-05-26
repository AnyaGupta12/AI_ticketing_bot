import streamlit as st
import sqlite3
import requests
import json
import os
import pickle
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from sentence_transformers import SentenceTransformer
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from pages.raise_ticket import save_chat_message, check_inactivity_and_close

# Constants
GEMINI_API_KEY = "AIzaSyCl-Ys-YuIoTBzN0fI8gcLmyIZsRp_zxWY"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    f"?key={GEMINI_API_KEY}"
)
CLOSING_KEYWORDS = ["thank you", "thanks", "bye", "goodbye", "see you"]

# Utility functions

def get_cutoff(minutes: int) -> datetime:
    return datetime.now() - timedelta(minutes=minutes)

@st.cache_resource
def get_connection():
    return sqlite3.connect("app.db", check_same_thread=False)

def get_ticket_details(conn, ticket_id):
    c = conn.cursor()
    c.execute(
        """
        SELECT product, problem_description, priority, company_id, status
          FROM Tickets
         WHERE id = ?
        """,
        (ticket_id,)
    )
    return c.fetchone()


def load_ticket_chat(ticket_id):
    conn = get_connection()
    c = conn.cursor()
    cutoff = get_cutoff(30)
    c.execute(
        """
        SELECT sender, message
          FROM chat_sessions
         WHERE ticket_id = ?
           AND timestamp >= ?
         ORDER BY timestamp
        """,
        (ticket_id, cutoff)
    )
    return c.fetchall()


def check_if_closing_message(message: str) -> bool:
    return any(kw in message.lower() for kw in CLOSING_KEYWORDS)


def build_prompt(history, context, ticket, user_input):
    recent = history[-10:] if len(history) > 10 else history

    convo = "\n".join(f"{sender.capitalize()}: {msg}" for sender, msg in recent)

    prod, desc, prio, cid, contact_name = ticket
    ticket_info = (
        f"Ticket #{st.session_state.get('ticket_id')} info:\n"
        f"- Product: {prod}\n"
        f"- Priority: {prio}\n"
        f"- Description: {desc}\n"
        f"- Company ID: {cid}\n"
        f"- Contact Name: {contact_name}"
    )

    context_block = context if context else "[No relevant KB context found]"

    prompt = f"""You are a highly knowledgeable support assistant whose job is to resolve customer issues quickly and accurately. You have access to:

1. **Ticket Details**  
{ticket_info}

2. **Relevant Knowledge Base Excerpts**  
{context_block}

3. **Recent Conversation History** (last 10 turns):  
{convo}

**Your instructions:**  
- **Primary Source:** If the KB excerpts contain all or part of the answer, use only that information—do not fabricate or add external data.  
- **Secondary Source:** If the KB is empty or insufficient, draw on your broader expertise or reliable online resources via Gemini to craft a complete, accurate, and concise response.  
- **Tone & Style:** Be professional, empathetic, and clear. Use bullet points or numbered steps if it helps the user.  
- **Scope:** Answer the user’s question directly. Do not initiate a handoff or mention internal processes.  
-** whenever there is "forward me to human agent query mark it as [HANDOFF_REQUIRED] in the response.

**User’s question:**  
{user_input}

**Assistant’s response:**  
"""
    return prompt.strip()


def call_gemini_llm(history, context: str, query: str, ticket: tuple) -> str:
    prompt = build_prompt(history, context, ticket, query)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    resp = requests.post(GEMINI_URL, headers=headers, data=json.dumps(payload))
    if resp.status_code != 200:
        return f"Error: {resp.status_code} - {resp.text}"
    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        # Optional JSON parsing
        try:
            parsed = json.loads(text)
            return parsed.get("response", text)
        except json.JSONDecodeError:
            return text
    except Exception as e:
        return f"Error parsing response: {e}"


def load_faiss_index(company_id: int):
    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    faiss_folder = f"faiss_index_company_{company_id}"
    if os.path.exists(faiss_folder):
        st.info(f"Loading FAISS index from {faiss_folder}")
        db = FAISS.load_local(
            folder_path=faiss_folder,
            embeddings=embedding_model,
            allow_dangerous_deserialization=True,
        )
        return db, embedding_model, faiss_folder
    st.warning(f"No FAISS index found for company {company_id}")
    return None, embedding_model, faiss_folder

def load_kb_to_faiss(conn, company_id: int, embedding_model, faiss_folder: str):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, content FROM KBDocument WHERE company_id = ?",
        (company_id,)
    )
    rows = cursor.fetchall()
    if not rows:
        st.warning("No KB documents found for this company.")
        return None
    docs = [f"{r[1]}. {r[2]}" for r in rows]
    # Build new index
    faiss_index = FAISS.from_texts(docs, embedding_model)
    # Persist to disk
    if os.path.exists(faiss_folder):
        import shutil
        shutil.rmtree(faiss_folder)
    faiss_index.save_local(faiss_folder)
    st.success(f"✅ KB loaded for company {company_id} ({len(docs)} docs)")
    return faiss_index

def get_top_k_chunks_faiss(query: str, faiss_folder: str, k: int = 3) -> list:
    if not os.path.exists(faiss_folder):
        st.warning(f"FAISS folder {faiss_folder} does not exist.")
        return []
    db = FAISS.load_local(
        folder_path=faiss_folder,
        embeddings=HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"),
        allow_dangerous_deserialization=True,
    )
    results = db.similarity_search(query, k=k)
    return [doc.page_content for doc in results]

def chatbot_page():
    # Ensure session and ticket
    if "session_id" not in st.session_state or "ticket_id" not in st.session_state:
        st.warning("Please start or resume a session from the home page.")
        st.stop()

    ticket_id = st.session_state["ticket_id"]
    conn = get_connection()
    ticket = get_ticket_details(conn, ticket_id)

    st.title("💬 Hack_X Support Chatbot")

    if not ticket:
        st.error("❌ Ticket not found.")
        return

    product, problem_description, priority, company_id, status = ticket

    history = load_ticket_chat(ticket_id)
    for sender, msg in history:
        st.chat_message(sender).write(msg)

    # Status checks
    if status.lower() == "closed":
        st.warning("🚫 This ticket has already been closed.")
        return
    
    if status.lower() == "handoff":
        st_autorefresh(interval=15000, limit=None, key="refresh")
        st.warning("🔁 Ticket escalated to human agent. Please wait.")

        user_input = st.chat_input("Your message…")
        if user_input:
            # echo & persist
            st.chat_message("user").write(user_input)
            save_chat_message(
                session_id=st.session_state["session_id"],
                sender="user",
                message=user_input,
                ticket_id=ticket_id
            )
            st.info("Your message has been sent to the agent.")
            # refresh to show the newly saved message
            st.rerun()

        # don’t return here—let the page stay open so autorefresh can pull in new agent replies
        return

    # Display ticket info
    st.markdown(f"**Ticket #{ticket_id}**")
    st.markdown(f"- **Product:** {product}")
    st.markdown(f"- **Priority:** {priority}")
    st.markdown(f"- **Description:** {problem_description}")
    st.markdown("---")

    # Load or create FAISS
    vectorstore, embedding_model, faiss_folder = load_faiss_index(company_id)
    faiss_index = load_kb_to_faiss(conn, company_id, embedding_model, faiss_folder)

    # Check inactivity
    if check_inactivity_and_close(st.session_state["session_id"], ticket_id):
        return

    # Display history
    history = load_ticket_chat(ticket_id)
    for sender, msg in history:
        st.chat_message(sender).write(msg)

    # User input
    user_input = st.chat_input("Ask about your issue...")
    if not user_input:
        return

    # Handle closing
    if check_if_closing_message(user_input):
        c = conn.cursor()
        c.execute("UPDATE Tickets SET status='closed' WHERE id=?", (ticket_id,))
        conn.commit()
        st.success("✅ Ticket marked as closed.")
        return

    # Retrieve KB context
    top_chunks = get_top_k_chunks_faiss(user_input, faiss_folder)
    context = "\n\n".join(top_chunks)

    # Call LLM
    bot_reply = call_gemini_llm(history, context, user_input, ticket)
    if "[HANDOFF_REQUIRED]" in bot_reply:
        conn.cursor().execute(
            "UPDATE Tickets SET status='Handoff' WHERE id=?", (ticket_id,)
        )
        conn.commit()
        st.warning("🔁 Ticket marked for human assistance.")
        st.rerun()

    # Display and save
    st.chat_message("user").write(user_input)
    st.chat_message("assistant").write(bot_reply)
    save_chat_message(st.session_state.session_id, "user", user_input, ticket_id)
    save_chat_message(st.session_state.session_id, "assistant", bot_reply, ticket_id)


# Run
if __name__ == "__main__":
    chatbot_page()
