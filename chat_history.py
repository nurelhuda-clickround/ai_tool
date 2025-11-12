# chat_history.py
import sqlite3
import os
import json
import plotly.io as pio
from plotly.graph_objs import Figure
from datetime import datetime, timedelta

DB_PATH = "chat_history.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check and create chat_history table
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_history'")
    if not c.fetchone():
        c.execute("""
            CREATE TABLE chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # Check and create generated_files table
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='generated_files'")
    if not c.fetchone():
        c.execute("""
            CREATE TABLE generated_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                username TEXT NOT NULL,
                file_path TEXT NOT NULL,
                query TEXT NOT NULL,
                history_index INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # Check and create generated_charts table
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='generated_charts'")
    if not c.fetchone():
        c.execute("""
            CREATE TABLE generated_charts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                username TEXT NOT NULL,
                chart_data TEXT NOT NULL,
                query TEXT NOT NULL,
                history_index INTEGER NOT NULL,
                render_method TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # Check and create user_sessions table
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_sessions'")
    if not c.fetchone():
        c.execute("""
            CREATE TABLE user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

    conn.commit()
    conn.close()

def save_message(username, conv_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO chat_history (username, conversation_id, role, content) VALUES (?, ?, ?, ?)",
        (username, conv_id, role, content)
    )
    conn.commit()
    conn.close()

def save_file_metadata(username, conv_id, file_path, query, history_index):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO generated_files (username, conversation_id, file_path, query, history_index) VALUES (?, ?, ?, ?, ?)",
        (username, conv_id, file_path, query, history_index)
    )
    conn.commit()
    conn.close()

def save_chart_metadata(username, conv_id, chart_data, render_method, query, history_index):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    chart_data_json = chart_data if isinstance(chart_data, str) else json.dumps(chart_data)
    c.execute(
        "INSERT INTO generated_charts (username, conversation_id, chart_data, query, history_index, render_method) VALUES (?, ?, ?, ?, ?, ?)",
        (username, conv_id, chart_data_json, query, history_index, render_method)
    )
    conn.commit()
    conn.close()

def save_session(session_id, username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO user_sessions (session_id, username, timestamp)
        VALUES (?, ?, ?)
    ''', (session_id, username, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def load_session(session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT session_id, username, timestamp FROM user_sessions WHERE session_id = ?",
        (session_id,)
    )
    row = c.fetchone()
    print(f"row: {row}")
    conn.close()
    if row:
        session_timestamp = datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S')
        if datetime.now() - session_timestamp < timedelta(hours=24):  # Expire after 24 hours
            return {"session_id": row[0], "username": row[1]}
    
    return None

def delete_session(session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "DELETE FROM user_sessions WHERE session_id = ?",
        (session_id,)
    )
    conn.commit()
    conn.close()

def load_conversations(username):
    """Return all conversation_ids for a user, sorted by last activity."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT conversation_id, MAX(timestamp)
        FROM chat_history
        WHERE username=?
        GROUP BY conversation_id
        ORDER BY MAX(timestamp) DESC
    """, (username,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def load_all_conversations(username):
    """Return all conversation messages for a user, sorted by last activity (latest timestamp)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT role, content,timestamp 
        FROM chat_history
        WHERE username = ?
        ORDER BY timestamp ASC
    """, (username,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]



def load_conversation_messages(username, conv_id, limit=None):
    """Load all (or last N) messages for a conversation."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if limit:
        c.execute("""
            SELECT role, content FROM chat_history
            WHERE username=? AND conversation_id=?
            ORDER BY id DESC LIMIT ?
        """, (username, conv_id, limit))
        rows = c.fetchall()[::-1]  # reverse to maintain chronological order
    else:
        c.execute("""
            SELECT role, content FROM chat_history
            WHERE username=? AND conversation_id=?
            ORDER BY id
        """, (username, conv_id))
        rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

def load_file_metadata(username, conv_id):
    """Load metadata for generated files in a conversation."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT file_path, query, history_index
        FROM generated_files
        WHERE username=? AND conversation_id=?
        ORDER BY history_index
    """, (username, conv_id))
    rows = c.fetchall()
    conn.close()
    return [
        {
            "username": username,
            "conv_id": conv_id,
            "file_path": row[0],
            "query": row[1],
            "history_index": row[2]
        } for row in rows
    ]

def load_chart_metadata(username, conv_id):
    """Load metadata for generated charts in a conversation."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT chart_data, query, history_index, render_method
        FROM generated_charts
        WHERE username=? AND conversation_id=?
        ORDER BY history_index
    """, (username, conv_id))
    rows = c.fetchall()
    conn.close()
    return [
        {
            "username": username,
            "conv_id": conv_id,
            "chart": {
                "chart_data": pio.from_json(row[0]) if row[3] == "plotly" else json.loads(row[0]),
                "render_method": row[3]
            },
            "query": row[1],
            "history_index": row[2]
        } for row in rows
    ]

def delete_conversation(username, conv_id):
    """Delete all messages, files, and charts for a specific conversation."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "DELETE FROM chat_history WHERE username=? AND conversation_id=?",
        (username, conv_id)
    )
    c.execute(
        "DELETE FROM generated_files WHERE username=? AND conversation_id=?",
        (username, conv_id)
    )
    c.execute(
        "DELETE FROM generated_charts WHERE username=? AND conversation_id=?",
        (username, conv_id)
    )
    conn.commit()
    conn.close()