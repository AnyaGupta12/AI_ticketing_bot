import streamlit as st
import sqlite3
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
from pages.raise_ticket import load_recent_chat, save_chat_message
import requests
import json

GEMINI_API_KEY = "AIzaSyCl-Ys-YuIoTBzN0fI8gcLmyIZsRp_zxWY"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY

def build_prompt(history, context, ticket, user_input):
    # 1. Take the last 10 messages (or fewer if history is shorter)
    recent = history[-10:] if len(history) > 10 else history

    # 2. Turn into "User: …" / "Bot: …" lines
    convo = "\n".join(f"{sender.capitalize()}: {msg}" for sender, msg in recent)

    # 3. Unpack ticket into named fields
    prod, desc, prio, cid = ticket
    ticket_info = (
        f"Ticket #{st.session_state.get('ticket_id')} info:\n"
        f"- Product: {prod}\n"
        f"- Priority: {prio}\n"
        f"- Description: {desc}"
    )

    # 4. Assemble full prompt
    prompt = f"""
You are a helpful support assistant. Continue the conversation below, then answer the final user question.

{ticket_info}

Conversation so far:
{convo}

Knowledge Base Context:
{context}

User: {user_input}

Assistant:"""
    return prompt.strip()

def call_gemini_llm(history, context: str, query: str, ticket: tuple) -> str:
    prompt = build_prompt(history, context, ticket, query)

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    headers = {"Content-Type": "application/json"}

    resp = requests.post(GEMINI_URL, headers=headers, data=json.dumps(payload))
    if resp.status_code == 200:
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        return f"Error: {resp.status_code} – {resp.text}"

# Setup embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Setup ChromaDB in-memory client
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="company_kb")

@st.cache_resource
def get_connection():
    return sqlite3.connect("app.db", check_same_thread=False)

def load_kb_to_chroma(conn, company_id):
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, content FROM KBDocument WHERE company_id = ?", (company_id,))
    kb_rows = cursor.fetchall()

    if kb_rows:
        # You can combine title + content as document text for better context
        docs = [f"{row[1]}. {row[2]}" for row in kb_rows]  # title + content
        ids = [f"kb-{row[0]}" for row in kb_rows]
        embeddings = embedding_model.encode(docs).tolist()

        # Clear existing docs for this company before adding new ones
        collection.delete(where={"company_id": company_id})
        collection.add(documents=docs, ids=ids, embeddings=embeddings, metadatas=[{"company_id": company_id}] * len(docs))
        st.success(f"✅ Knowledge Base loaded for company ID {company_id} with {len(docs)} documents.")
        
def get_top_k_chunks(query, k=3):
    query_embedding = embedding_model.encode([query])[0].tolist()
    results = collection.query(query_embeddings=[query_embedding], n_results=k)
    return results['documents'][0] if results['documents'] else []

def chatbot_page():

    st.title("💬 Hack_X Support Chatbot")

    # --- Ensure required session info exists ---
    if "session_id" not in st.session_state or "user_name" not in st.session_state:
        st.warning("Session not initialized. Please go to the home page to start or resume a chat.")
        st.stop()

    # --- Load chat history once per session ---
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = load_recent_chat(st.session_state["session_id"])
    
    # --- Display existing messages ---
    for sender, msg in st.session_state.chat_history:
        with st.chat_message(sender):
            st.write(msg)

    ticket_id = st.session_state.get("ticket_id")
    if not ticket_id:
        st.warning("⚠️ No ticket found. Please raise a ticket first.")
        return

    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT product, problem_description, priority, company_id FROM Tickets WHERE id = ?", (ticket_id,))
    ticket = c.fetchone()

    if ticket:
        product, problem_description, priority, company_id = ticket
        st.markdown(f"**Ticket #{ticket_id}**")
        st.markdown(f"- **Product:** {product}")
        st.markdown(f"- **Priority:** {priority}")
        st.markdown(f"- **Description:** {problem_description}")
        st.markdown("---")
    else:
        st.error("❌ Ticket not found.")
        return

    # Load KB into Chroma for this company
    load_kb_to_chroma(conn, company_id)

    user_input = st.chat_input("Ask about your issue...")
    if user_input:
        # 1. Pull in the last 10 messages for context
        history = st.session_state.chat_history

        # 2. Get the top-k KB chunks
        top_chunks = get_top_k_chunks(user_input, k=3)
        kb_context = "\n\n".join(top_chunks)

        # 3. Fetch the ticket metadata you unpacked earlier
        #    (Make sure `ticket = c.fetchone()` ran above in your code)
        #    e.g. ticket = (product, desc, prio, company_id)

        # 4. Call the LLM with history + KB + ticket info baked in
        bot_reply = call_gemini_llm(
            history=history,
            context=kb_context,
            query=user_input,
            ticket=ticket
        )

        # 5. Display both sides
        st.chat_message("user").write(user_input)
        st.chat_message("bot").write(bot_reply)

        # 6. Append to session_state and save to DB
        st.session_state.chat_history.extend([
            ("user", user_input),
            ("bot", bot_reply)
        ])
        save_chat_message(
            session_id=st.session_state["session_id"],
            user_name=st.session_state["user_name"],
            sender="user",
            message=user_input,
            ticket_id=st.session_state["ticket_id"]
        )
        save_chat_message(
            session_id=st.session_state["session_id"],
            user_name=st.session_state["user_name"],
            sender="bot",
            message=bot_reply,
            ticket_id=st.session_state["ticket_id"]
        )


    for sender, msg in st.session_state.chat_history:
        with st.chat_message(sender):
            st.write(msg)
    st.markdown("---")

chatbot_page()
