## 🛠️ 3. Tech Stack Description

| Layer             | Technology                            | Purpose                                        |
| ----------------- | ------------------------------------- | ---------------------------------------------- |
| **Frontend**      | Streamlit                             | Rapid UI, chat components                      |
| **Backend & DB**  | SQLite                                | Lightweight data store for tickets and chats   |
| **Embeddings**    | sentence-transformers, LangChain      | Generate semantic vectors for KB docs          |
| **Vector DB**     | FAISS (via LangChain\[community])     | On-disk, per-company semantic search           |
| **LLM API**       | Google Gemini 2.0 Flash               | AI assistant for both customer and agent       |
| **Orchestration** | Python & Streamlit pages              | Routing, session management, auto-refresh      |
| **Deployment**    | Streamlit Community Cloud (or other)  | One-click deploy; supports Python & flat files |
| **Extras**        | streamlit-autorefresh, requests, json | Live chat and API calls                        |

---