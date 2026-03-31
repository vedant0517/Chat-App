import sqlite3
import datetime
import os

DB_FILE = os.environ.get(
    "CHATAPP_DB_FILE",
    os.path.join(os.path.dirname(__file__), "chat_database.db"),
)

def _get_conn():
    """Get a thread-safe SQLite connection with WAL mode."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                message_text TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                date TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS banned_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                banned_at TEXT NOT NULL,
                banned_by TEXT NOT NULL
            )
        ''')
        conn.commit()
    finally:
        conn.close()

def add_user(username: str, password_hash: str) -> bool:
    try:
        conn = _get_conn()
        try:
            cursor = conn.cursor()
            now = datetime.datetime.now().isoformat(timespec="seconds")
            cursor.execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                           (username, password_hash, now))
            conn.commit()
            return True
        finally:
            conn.close()
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"[DB ERROR] add_user: {e}")
        return False

def verify_user(username: str, password_hash: str) -> bool:
    try:
        conn = _get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row and row[0] == password_hash:
                return True
            return False
        finally:
            conn.close()
    except Exception as e:
        print(f"[DB ERROR] verify_user: {e}")
        return False

def check_user_exists(username: str) -> bool:
    try:
        conn = _get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return row is not None
        finally:
            conn.close()
    except Exception as e:
        print(f"[DB ERROR] check_user_exists: {e}")
        return False

def save_message(sender: str, text: str, timestamp: str, date: str) -> None:
    try:
        conn = _get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO history (sender, message_text, timestamp, date) VALUES (?, ?, ?, ?)",
                           (sender, text, timestamp, date))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"[DB ERROR] save_message: {e}")

def clear_history() -> bool:
    try:
        conn = _get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM history")
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as e:
        print(f"[DB ERROR] clear_history: {e}")
        return False

def get_recent_history(limit: int = 50) -> list:
    messages = []
    try:
        conn = _get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT sender, message_text, timestamp FROM history ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
        finally:
            conn.close()

        rows.reverse()
        for row in rows:
            messages.append({
                "type": "message",
                "from": row[0],
                "text": row[1],
                "ts": row[2]
            })
    except Exception as e:
        print(f"[DB ERROR] get_recent_history: {e}")
        
    return messages

def update_password(username: str, new_hash: str) -> bool:
    try:
        conn = _get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hash, username))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    except Exception as e:
        print(f"[DB ERROR] update_password: {e}")
        return False

def ban_user(username: str, banned_by: str) -> bool:
    try:
        conn = _get_conn()
        try:
            cursor = conn.cursor()
            now = datetime.datetime.now().isoformat(timespec="seconds")
            cursor.execute("INSERT OR IGNORE INTO banned_users (username, banned_at, banned_by) VALUES (?, ?, ?)",
                           (username, now, banned_by))
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as e:
        print(f"[DB ERROR] ban_user: {e}")
        return False

def is_banned(username: str) -> bool:
    try:
        conn = _get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM banned_users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return row is not None
        finally:
            conn.close()
    except Exception as e:
        print(f"[DB ERROR] is_banned: {e}")
        return False

def unban_user(username: str) -> bool:
    try:
        conn = _get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM banned_users WHERE username = ?", (username,))
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as e:
        print(f"[DB ERROR] unban_user: {e}")
        return False

init_db()
