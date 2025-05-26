import streamlit as st
import sqlite3
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
from pages.raise_ticket import save_chat_message, check_inactivity_and_close
import requests
import json
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh



def get_cutoff(minutes: int) -> datetime:
    return datetime.now() - timedelta(minutes=minutes)


GEMINI_API_KEY = "AIzaSyCl-Ys-YuIoTBzN0fI8gcLmyIZsRp_zxWY"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY


def load_ticket_chat(ticket_id):
    conn = sqlite3.connect("app.db", check_same_thread=False)
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

CLOSING_KEYWORDS = ["thank you", "thanks", "bye", "goodbye", "see you"]

def check_if_closing_message(message):
    return any(keyword in message.lower() for keyword in CLOSING_KEYWORDS)

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

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    headers = {"Content-Type": "application/json"}

    resp = requests.post(GEMINI_URL, headers=headers, data=json.dumps(payload))
    
    if resp.status_code == 200:
        try:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            # Try to parse it as JSON if it looks like a JSON object
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict) and "response" in parsed:
                    return parsed["response"]
                return text
            except json.JSONDecodeError:
                return text

        except (KeyError, IndexError) as e:
            return f"Error parsing response: {e}"
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

    user_name = st.session_state.get("user_name")

    st.title("💬 Hack_X Support Chatbot")

    # 1. Ensure session + ticket exist
    if "session_id" not in st.session_state or "ticket_id" not in st.session_state:
        st.warning("Please start or resume a session from the home page.")
        st.stop()
    
    history = load_ticket_chat(st.session_state["ticket_id"])
    for sender, msg in history:
        with st.chat_message(sender):
            st.write(msg)

    ticket_id = st.session_state.get("ticket_id")
    if not ticket_id:
        st.warning("⚠️ No ticket found. Please raise a ticket first.")
        return

    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT product, problem_description, priority, company_id, status FROM Tickets WHERE id = ?", (ticket_id,))
    ticket = c.fetchone()

    if ticket:
        product, problem_description, priority, company_id, status = ticket

        if status.lower() == "closed":
            st.warning("🚫 This ticket has already been closed. No further messages can be sent.")
            return
            # Only auto-refresh if this ticket is in handoff
        if status.lower() == "handoff":
            st_autorefresh(interval=15000, limit=None, key="chat_refresh")
        
        if status.lower() == "handoff":
            st.warning("🔁 This ticket has been escalated to a human agent. Please wait for them to reply here.")
            # Still allow the user to type, but skip LLM
            user_input = st.chat_input("Your message…")
            if user_input:
                # echo back their message
                st.chat_message("user").write(user_input)
                # save it so the agent sees it
                save_chat_message(
                    session_id=st.session_state["session_id"],
                    sender="user",
                    message=user_input,
                    ticket_id=ticket_id
                )
                # optionally remind again
                st.info("Your message has been sent to the agent. They'll reply in this same window.")
            return   # skip the rest of the LLM logic


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

    if check_inactivity_and_close(st.session_state["session_id"], ticket_id):
        return  # Exit the chatbot

    user_input = st.chat_input("Ask about your issue...")
    if user_input:

         # Check for closing message
        if check_if_closing_message(user_input):
            c.execute("UPDATE Tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
            conn.commit()
            st.success("✅ Ticket marked as closed. Thank you!")
            return  # stop further interaction

        # 2. Get the top-k KB chunks
        top_chunks = get_top_k_chunks(user_input, k=3)
        kb_context = "\n\n".join(top_chunks)

        # 3. Fetch the ticket metadata you unpacked earlier
        #    (Make sure ticket = c.fetchone() ran above in your code)
        #    e.g. ticket = (product, desc, prio, company_id)

        # 4. Call the LLM
        bot_reply = call_gemini_llm(
            history=history,
            context=kb_context,
            query=user_input,
            ticket=ticket
        )

        # 4.5 Check for LLM-triggered handoff
        if "[HANDOFF_REQUIRED]" in bot_reply:
            c.execute("UPDATE Tickets SET status = 'Handoff' WHERE id = ?", (ticket_id,))
            conn.commit()
            st.warning("🔁 Your ticket has been marked for human assistance.")
            st.rerun()

            # Optional: remove the marker before displaying
            bot_reply = bot_reply.replace("[HANDOFF_REQUIRED]", "").strip()


        # 5. Display both sides
        st.chat_message("user").write(user_input)
        st.chat_message("bot").write(bot_reply)

        save_chat_message(
            session_id=st.session_state["session_id"],
            sender="user",
            message=user_input,
            ticket_id=st.session_state["ticket_id"]
        )
        save_chat_message(
            session_id=st.session_state["session_id"],
            sender="assistant",
            message=bot_reply,
            ticket_id=st.session_state["ticket_id"]
        )

chatbot_page()
