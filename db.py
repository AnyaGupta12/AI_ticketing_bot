# File: db.py
import sqlite3
import threading

# Single shared connection
_conn = sqlite3.connect(
    "app.db",
    check_same_thread=False,
    timeout=20,               # wait up to 20s for locks
    isolation_level=None      # autocommit mode for WAL
)
# Enable Write-Ahead Logging
_conn.execute("PRAGMA journal_mode = WAL;")
_conn.execute("PRAGMA foreign_keys = ON;")

# A simple lock so only one thread writes at a time
_lock = threading.Lock()

def get_conn():
    return _conn

def execute(query, params=()):
    with _lock:
        cur = _conn.cursor()
        cur.execute(query, params)
        return cur

def executemany(query, seq_of_params):
    with _lock:
        cur = _conn.cursor()
        cur.executemany(query, seq_of_params)
        return cur

def init_db():
    execute("""
        CREATE TABLE IF NOT EXISTS Company (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    execute("""
        CREATE TABLE IF NOT EXISTS User (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','agent')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(company_id) REFERENCES Company(id) ON DELETE CASCADE
        );
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS Tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            company_id INTEGER,
            product TEXT NOT NULL,
            problem_description TEXT NOT NULL,
            priority TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            contact_name TEXT,         -- NEW column to store user's name
            status TEXT DEFAULT 'Open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES User(id),
            FOREIGN KEY(company_id) REFERENCES Company(id)
        );
    """)
    # Ensure chat_sessions uses a nullable session_id and is indexed by ticket_id
    execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id   INTEGER NOT NULL,
        session_id  TEXT,                        -- now nullable
        user_name   TEXT NOT NULL,
        sender      TEXT 
                    CHECK(sender IN ('user','assistant')) 
                    NOT NULL,
        message     TEXT NOT NULL,
        timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(ticket_id) REFERENCES Tickets(id)
    );
    """)

    # Make lookups by ticket_id fast
    execute("""
    CREATE INDEX IF NOT EXISTS idx_chat_ticket
    ON chat_sessions(ticket_id);
    """)

    
    execute("""
        CREATE TABLE IF NOT EXISTS KBDocument (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(company_id) REFERENCES Company(id) ON DELETE CASCADE
        );
    """)
