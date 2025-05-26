# File: pages/agent_chat.py
import streamlit as st
import sqlite3
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# ——————————————————————————————————————————————
# Embedding & Chroma setup
# ——————————————————————————————————————————————
from sentence_transformers import SentenceTransformer
import chromadb

# 1. Sentence-Transformer model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


GEMINI_API_KEY = "AIzaSyCl-Ys-YuIoTBzN0fI8gcLmyIZsRp_zxWY"

# 2. In-memory Chroma client & collection
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="company_kb")

def load_kb_to_chroma(conn, company_id):
    """Load all KB docs for this company into Chroma."""
    cur = conn.cursor()
    cur.execute("SELECT id, title, content FROM KBDocument WHERE company_id = ?", (company_id,))
    rows = cur.fetchall()
    if not rows:
        return
    docs   = [f"{r[1]}. {r[2]}" for r in rows]
    ids    = [f"kb-{r[0]}"    for r in rows]
    embeds = embedding_model.encode(docs).tolist()
    # remove old entries and add fresh
    collection.delete(where={"company_id": company_id})
    collection.add(
      documents=docs,
      ids=ids,
      embeddings=embeds,
      metadatas=[{"company_id": company_id}]*len(docs)
    )

def get_top_k_chunks(query, k=3):
    """Return top-k documents strings for a query."""
    embed = embedding_model.encode([query])[0].tolist()
    res   = collection.query(query_embeddings=[embed], n_results=k)
    return res["documents"][0] if res["documents"] else []

# ——————————————————————————————————————————————
# LLM prompt + call
# ——————————————————————————————————————————————
import requests, json
from datetime import datetime

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
    "?key=" + GEMINI_API_KEY
)

def build_prompt(history, context, ticket_meta, user_input):
    """Assemble a plain-text prompt from chat history, KB and ticket."""
    # history is list of (sender, message)
    convo = "\n".join(f"{s.capitalize()}: {m}" for s, m in history[-10:])
    prod, desc, prio, cid, contact = ticket_meta
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
    """Send assembled prompt to Gemini and return the assistant’s text."""
    prompt = build_prompt(history, context, ticket_meta, query)
    payload = {"contents":[{"parts":[{"text": prompt}]}]}
    resp = requests.post(GEMINI_URL, json=payload)
    if resp.status_code!=200:
        return f"Error {resp.status_code}: {resp.text}"
    txt = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    return txt


def get_cutoff(minutes: int) -> datetime:
    return datetime.now() - timedelta(minutes=minutes)

def get_conn():
    return sqlite3.connect("app.db", check_same_thread=False)

def agent_chat_page():
    # ─── Refresh-key init ─────────────────────────────────────────────
    if "refresh_key" not in st.session_state:
        st.session_state["refresh_key"] = 0

    # ─── Auto-refresh that restarts after each reply ─────────────────
    st_autorefresh(
        interval=15_000,
        limit=None,
        key=f"chat_refresh_{st.session_state['refresh_key']}"
    )

    ticket_id = st.session_state.get("current_ticket_id")
    st.title(f"🛠️ Agent Chat – Ticket #{ticket_id}")

    if not ticket_id:
        st.error("No ticket selected. Go back to the dashboard.")
        st.stop()

    conn = get_conn()
    c = conn.cursor()

    # ─── Fetch ticket metadata ─────────────────────────────────────
    c.execute("""
        SELECT product, problem_description, priority, company_id, contact_name
          FROM Tickets
         WHERE id = ?
    """, (ticket_id,))
    ticket_meta = c.fetchone()  # (prod, desc, prio, company_id, contact_name)

    # ─── Load recent chat history for LLM context ─────────────────
    cutoff = get_cutoff(30)
    c.execute("""
        SELECT sender, message
          FROM chat_sessions
         WHERE ticket_id = ?
           AND timestamp >= ?
         ORDER BY timestamp
    """, (ticket_id, cutoff))
    ticket_chat_history = [(sender, message) for sender, message in c.fetchall()]

    # ─── Now split into two columns ───────────────────────────────
    col1, col2 = st.columns(2)

    # … continue with your col1 and col2 code …


    # ================================
    # 👤 Agent ↔ User Chat (Left Side)
    # ================================
    with col1:
        st.subheader("👤 Agent ↔ User Chat")

        # Load last 30 mins of chat
        cutoff = get_cutoff(30)
        c.execute(
            """
            SELECT sender, message, timestamp
              FROM chat_sessions
             WHERE ticket_id = ?
               AND timestamp >= ?
             ORDER BY timestamp
            """,
            (ticket_id, cutoff)
        )
        rows = c.fetchall()

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

        # 1. initialize state
        if "bot_history" not in st.session_state:
            st.session_state["bot_history"] = []

        # 2. show previous bot↔agent chat
        for role, msg in st.session_state["bot_history"]:
            with st.chat_message(role):
                st.write(msg)
            # restart refresh timer
            st.session_state["refresh_key"] += 1

        # 3. input prompt
        agent_to_bot = st.chat_input("Ask the assistant…", key="bot_chat_input")

        if agent_to_bot:
            # a) append user message
            st.session_state["bot_history"].append(("user", agent_to_bot))
            with st.chat_message("user"):
                st.write(agent_to_bot)

            # b) ensure KB is loaded for this company
            #    assume you loaded ticket_meta above: (product,desc,prio,company_id,contact)
            load_kb_to_chroma(conn, ticket_meta[3])

            # c) retrieve top-3 contexts
            kb_context = "\n\n".join(get_top_k_chunks(agent_to_bot, k=3))

            # d) call LLM
            bot_reply = call_gemini_llm(
                history=ticket_chat_history + st.session_state["bot_history"],
                context=kb_context,
                query=agent_to_bot,
                ticket_meta=ticket_meta
            )

            # e) append & display
            st.session_state["bot_history"].append(("assistant", bot_reply))
            with st.chat_message("assistant"):
                st.write(bot_reply)


if __name__ == "__main__":
    agent_chat_page()