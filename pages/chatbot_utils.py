import sqlite3
import numpy as np
import openai
from db import get_conn

client = openai.OpenAI()  # Uses API key from environment or config

def get_embedding(text, model="text-embedding-ada-002"):
    response = client.embeddings.create(
        input=[text],
        model=model,
    )
    return np.array(response.data[0].embedding, dtype=np.float32)


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def query_kb(query, company_id):
    conn = get_conn()
    c = conn.cursor()
    query_vec = get_embedding(query)

    c.execute("SELECT title, content, embedding FROM KBDocument WHERE company_id = ? AND embedding IS NOT NULL", (company_id,))
    best_score = -1
    best_result = None

    for title, content, emb_blob in c.fetchall():
        kb_vec = np.frombuffer(emb_blob, dtype=np.float32)
        score = cosine_similarity(query_vec, kb_vec)
        if score > best_score:
            best_score = score
            best_result = content

    return best_result if best_result else "Sorry, no relevant knowledge found."
