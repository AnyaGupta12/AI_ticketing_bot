# File: pages/agent_chat.py
import streamlit as st
import sqlite3
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from sentence_transformers import SentenceTransformer
import os
import shutil

# ——————————————————————————————————————————————
# Embedding & FAISS setup
# ——————————————————————————————————————————————
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings


# 2. LangChain embedding wrapper for FAISS
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

GEMINI_API_KEY = "AIzaSyCl-Ys-YuIoTBzN0fI8gcLmyIZsRp_zxWY"

def load_kb_to_chroma(conn, company_id):
    """
    Load all KB docs for this company into a FAISS index.
    (Function name unchanged for backward compatibility.)
    """
    cur = conn.cursor()
    cur.execute("SELECT id, title, content FROM KBDocument WHERE company_id = ?", (company_id,))
    rows = cur.fetchall()
    if not rows:
        return

    # Prepare documents
    docs = [f"{r[1]}. {r[2]}" for r in rows]

    # Persistence folder
    folder = f"faiss_agent_{company_id}"
    # Remove old index if present
    if os.path.exists(folder):
        shutil.rmtree(folder)

    # Build and save FAISS index
    faiss_index = FAISS.from_texts(docs, embedding_model)
    faiss_index.save_local(folder)
    st.success(f"✅ KB loaded for company {company_id} ({len(docs)} docs)")

def get_top_k_chunks(query, k=3):
    """
    Return top-k document strings for a query, using the FAISS index.
    """
    # We need company_id to know which folder—but the index was built
    # per-page during the agent’s turn, so we assume it’s in session.
    # Here we infer folder from last-loaded company_id in session.
    cid = st.session_state.get("current_company_id")
    if not cid:
        return []

    folder = f"faiss_agent_{cid}"
    if not os.path.exists(folder):
        return []

    # Load the FAISS index
    db = FAISS.load_local(folder, embedding_model, allow_dangerous_deserialization=True)
    results = db.similarity_search(query, k=k)
    return [doc.page_content for doc in results]

# ——————————————————————————————————————————————
# LLM prompt + call
# ——————————————————————————————————————————————
import requests, json

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
    f"?key={GEMINI_API_KEY}"
)

def build_prompt(history, context, ticket_meta, user_input):
    convo = "\n".join(f"{s.capitalize()}: {m}" for s, m in history[-10:])
    prod, desc, prio, cid, contact = ticket_meta
    # store company_id in session so get_top_k_chunks can pick it up
    st.session_state["current_company_id"] = cid

    info = (
        f"Ticket #{st.session_state['current_ticket_id']}:\n"
        f"- Product: {prod}\n"
        f"- Priority: {prio}\n"
        f"- Description: {desc}\n"
        f"- Company ID: {cid}\n"
        f"- Contact: {contact}"
    )
    return f"""
You are a helpful support assistant. Use the ticket info and the knowledge base to answer.

{info}

Conversation so far:
{convo}

Knowledge Base:
{context}

User: {user_input}

Assistant:
""".strip()

def call_gemini_llm(history, context, query, ticket_meta):
    prompt = build_prompt(history, context, ticket_meta, query)
    payload = {"contents":[{"parts":[{"text": prompt}]}]}
    resp = requests.post(GEMINI_URL, json=payload)
    if resp.status_code!=200:
        return f"Error {resp.status_code}: {resp.text}"
    txt = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    return txt

# ——————————————————————————————————————————————
# DB + Chat helpers
# ——————————————————————————————————————————————
def get_cutoff(minutes: int) -> datetime:
    return datetime.now() - timedelta(minutes=minutes)

def get_conn():
    return sqlite3.connect("app.db", check_same_thread=False)

# ——————————————————————————————————————————————
# Page entrypoint
# ——————————————————————————————————————————————
def agent_chat_page():
    # ─── Refresh-key init ─────────────────────
    if "refresh_key" not in st.session_state:
        st.session_state["refresh_key"] = 0

    st_autorefresh(
        interval=15_000,
        limit=None,
        key=f"chat_refresh_{st.session_state['refresh_key']}"
    )

    ticket_id = st.session_state.get("current_ticket_id")
    if not ticket_id:
        st.error("No ticket selected. Go back to the dashboard.")
        st.stop()

    conn = get_conn()
    c = conn.cursor()

    # ─── Fetch ticket metadata ───────────────
    c.execute("""
        SELECT product, problem_description, priority, company_id, contact_name
          FROM Tickets
         WHERE id = ?
    """, (ticket_id,))
    ticket_meta = c.fetchone()
    if not ticket_meta:
        st.error("Ticket not found.")
        return

    st.title(f"🛠️ Agent Chat – Ticket #{ticket_id}")

    # ─── Load KB into FAISS ────────────────────
    load_kb_to_chroma(conn, ticket_meta[3])

    # ─── Load recent chat history ──────────────
    cutoff = get_cutoff(30)
    c.execute("""
        SELECT sender, message, timestamp
          FROM chat_sessions
         WHERE ticket_id = ?
           AND timestamp >= ?
         ORDER BY timestamp
    """, (ticket_id, cutoff))
    rows = c.fetchall()

    col1, col2 = st.columns(2)

    # ================================
    # 👤 Agent ↔ User Chat (Left Side)
    # ================================
    with col1:
        st.subheader("👤 Agent ↔ User Chat")

        if not rows:
            st.warning("No chat history in the last 30 minutes.")
        else:
            for sender, message, _ in rows:
                role = "user" if sender == "user" else "assistant"
                with st.chat_message(role):
                    st.write(message)

        agent_input = st.chat_input("Your response to user…", key="user_chat_input")
        if agent_input:
            c.execute(
                """
                INSERT INTO chat_sessions 
                  (session_id, user_name, sender, message, timestamp, ticket_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "agent-session",
                    st.session_state["user_name"],
                    "assistant",
                    agent_input,
                    datetime.now(),
                    ticket_id
                )
            )
            conn.commit()
            with st.chat_message("assistant"):
                st.write(agent_input)
            st.session_state["refresh_key"] += 1
            st.rerun()

        if st.button("✅ Mark Ticket Closed"):
            c.execute(
                """
                UPDATE Tickets
                   SET status = 'Closed', user_id = ?
                 WHERE id = ?
                """,
                (st.session_state["user_id"], ticket_id)
            )
            conn.commit()
            st.success("Ticket closed.")
            del st.session_state["current_ticket_id"]
            st.switch_page("pages/agent_dashboard.py")

    # ==================================
    # 🤖 Agent ↔ Bot Assistant (Right Side)
    # ==================================
    with col2:
        st.subheader("🤖 Agent Assistant")

        # Bot history in session
        if "bot_history" not in st.session_state:
            st.session_state["bot_history"] = []

        # Show history
        for role, msg in st.session_state["bot_history"]:
            with st.chat_message(role):
                st.write(msg)
            st.session_state["refresh_key"] += 1

        agent_to_bot = st.chat_input("Ask the assistant…", key="bot_chat_input")
        if agent_to_bot:
            st.session_state["bot_history"].append(("user", agent_to_bot))
            with st.chat_message("user"):
                st.write(agent_to_bot)

            # retrieve FAISS contexts
            kb_context = "\n\n".join(get_top_k_chunks(agent_to_bot, k=3))

            bot_reply = call_gemini_llm(
                history=[(r[0], r[1]) for r in rows] + st.session_state["bot_history"],
                context=kb_context,
                query=agent_to_bot,
                ticket_meta=ticket_meta
            )

            st.session_state["bot_history"].append(("assistant", bot_reply))
            with st.chat_message("assistant"):
                st.write(bot_reply)

if __name__ == "__main__":
    agent_chat_page()
