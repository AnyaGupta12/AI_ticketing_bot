## 🏗️ 2. Architecture Documentation

```text
+----------------------+      +----------------+
|  Streamlit Frontend  |      |  Streamlit     |
|  (pages/*.py)        |<---->|  Backend      |
+----------+-----------+      +--------+-------+
           |                            |
           v                            v
+----------------------+     +------------------+
|  SQLite (app.db)     |     |  FAISS Indexes   |
|  - Tickets           |     |  (per company)   |
|  - KBDocument        |     |  saved in fs     |
|  - chat_sessions     |     +------------------+
+----------------------+
```

1. **`pages/home.py`**  – Company signup, login, ticket creation
2. **`pages/raise_ticket.py`**  – Save user messages & metadata
3. **`pages/chatbot.py`**  – Customer-facing AI chatbot using FAISS + Gemini
4. **`pages/agent_dashboard.py`**  – List and manage tickets for agents
5. **`pages/agent_chat.py`**  – Agent ↔ User and Agent Assist chat
6. **`scripts/init_db.py`**  – Initializes SQLite schema and seeds
7. **Vector Search**: Builds per-company FAISS indexes under `faiss_index_company_{company_id}`
8. **LLM Integration**: Prompts via `build_prompt()`, calls Google Gemini REST API
9. **Session & Refresh**: Uses `st.session_state` and `streamlit-autorefresh`

---