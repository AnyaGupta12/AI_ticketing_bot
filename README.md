# AI-Powered Ticketing & Support Platform

An end-to-end, multi-tenant customer support and ticketing system built with Streamlit, SQLite, and AI/ML (Google Gemini, LangChain + FAISS).
Customers chat with an AI-driven bot; agents get an AI copilot. Tickets are auto-classified, and knowledge-base searches are powered by FAISS.

---

## 📦 1. Setup Instructions

### Prerequisites

* Python 3.10+
* Git
* (Optional) `virtualenv` or `conda` for isolation

### 1. Clone the repository

```bash
git clone https://github.com/AnyaGupta12/AI_ticketing_bot
cd ai-ticketing-platform
```

### 2. Create & activate a virtual environment

```bash
python -m venv venv
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note**: `requirements.txt` includes:
>
> ```text
>streamlit
>streamlit-autorefresh
>passlib
>PyMuPDF
>requests
>pandas
>matplotlib
>seaborn
>chromadb
>sentence-transformers
>torch
>numpy
>protobuf==3.20.3
>faiss-cpu
>langchain
>langchain[community]
> ```
>
> Adjust versions as needed.

### 4. Initialize the database

```bash
python db.py
```

This creates `app.db` with tables:

* **Companies** (`id`, `name`, `settings`, …)
* **Tickets** (`id`, `company_id`, `product`, `description`, `priority`, `status`, `contact_name`, …)
* **KBDocument** (`id`, `company_id`, `title`, `content`, …)
* **chat\_sessions** (`session_id`, `sender`, `message`, `timestamp`, `ticket_id`)

### 5. Configure API key

Put your API key where needed in chatbot and agent_chat file
```env
GEMINI_API_KEY=YOUR_GOOGLE_GENERATIVE_API_KEY
```

### 6. Run the app locally

```bash
streamlit run app.py
```

Open your browser to `http://localhost:8501`.

---