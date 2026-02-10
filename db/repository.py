# db/repository.py
import os
import json
import sqlite3
from datetime import datetime, date

# ---------------------------
# DB PATH (Railway-safe)
# ---------------------------
DB_PATH = os.getenv("DB_PATH", os.path.join("data", "app.db"))

# Optional: allow bootstrap admin by env
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


# ==========================================================
# INTERNAL HELPERS
# ==========================================================

def _ensure_parent_dir(path: str):
    parent = os.path.dirname(path)
    if parent and parent != "/" and not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except Exception:
            pass


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cur.fetchone() is not None


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    cur = conn.cursor()
    try:
        cur.execute(f"PRAGMA table_info({table_name})")
        cols = [row[1] for row in cur.fetchall()]
        return column_name in cols
    except Exception:
        return False


def _apply_min_schema(conn: sqlite3.Connection):
    """
    Minimal schema that supports the whole app.
    This avoids Railway failing because schema.sql isn't present.
    """
    cur = conn.cursor()

    # Users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'Analyst',
            is_active INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Reviews
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            industry TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # KPI Inputs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kpi_inputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            kpi_id TEXT NOT NULL,
            value REAL DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(review_id, kpi_id)
        )
    """)

    # Scores (for benchmarking)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            kpi_id TEXT NOT NULL,
            score REAL DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(review_id, kpi_id)
        )
    """)

    # Exports (track export usage)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            review_id INTEGER,
            export_type TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Optional subscriptions table (if you later add billing plans)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            can_export INTEGER DEFAULT 1,
            export_limit_per_day INTEGER DEFAULT 999,
            can_create_review INTEGER DEFAULT 1,
            review_limit INTEGER DEFAULT 999,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()


def _ensure_financial_raw_shape(conn: sqlite3.Connection):
    """
    Fixes Railway mismatch issues where some deployments used `data_json`
    and others used `payload`. We support BOTH.
    """
    cur = conn.cursor()

    # Create table with BOTH columns (safe)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS financial_raw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            payload TEXT,
            data_json TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # If an older table exists without one of the columns, add it
    if not _column_exists(conn, "financial_raw", "payload"):
        try:
            cur.execute("ALTER TABLE financial_raw ADD COLUMN payload TEXT")
        except Exception:
            pass

    if not _column_exists(conn, "financial_raw", "data_json"):
        try:
            cur.execute("ALTER TABLE financial_raw ADD COLUMN data_json TEXT")
        except Exception:
            pass

    conn.commit()


def _ensure_admin_is_active(conn: sqlite3.Connection):
    """
    Ensures the bootstrap admin (ADMIN_EMAIL) is active and role=Admin.
    This fixes: 'Account pending approval. Please wait for admin'
    when you log in as admin.
    """
    if not ADMIN_EMAIL:
        return

    cur = conn.cursor()
    cur.execute("SELECT id, email, role, is_active FROM users WHERE lower(email)=?", (ADMIN_EMAIL,))
    row = cur.fetchone()
    if row:
        # force activate
        cur.execute(
            "UPDATE users SET role=?, is_active=1 WHERE id=?",
            ("Admin", row["id"])
        )
        conn.commit()


# ==========================================================
# CONNECTION
# ==========================================================

def get_connection():
    _ensure_parent_dir(DB_PATH)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Improve stability
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass

    # Ensure schema + migrations
    _apply_min_schema(conn)
    _ensure_financial_raw_shape(conn)
    _ensure_admin_is_active(conn)

    return conn


def get_conn():
    return get_connection()


# ==========================================================
# USERS / AUTH
# ==========================================================

def get_user_by_email(email: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE lower(email)=?", (str(email).strip().lower(),))
    row = cur.fetchone()
    conn.close()
    return row


def create_user(email: str, password: str, role: str = "Analyst", is_active: int = 0):
    """
    Default users are inactive (approval needed), BUT:
    - Admin/CEO are activated immediately
    - Also auto-activate the bootstrap ADMIN_EMAIL
    """
    email_norm = str(email).strip().lower()
    role_norm = (role or "Analyst").strip()

    if role_norm.lower() in ("admin", "ceo"):
        is_active = 1
    if ADMIN_EMAIL and email_norm == ADMIN_EMAIL:
        role_norm = "Admin"
        is_active = 1

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users (email, password, role, is_active)
        VALUES (?, ?, ?, ?)
    """, (email_norm, str(password), role_norm, int(is_active)))

    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def set_user_active(email: str, is_active: int = 1):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_active=? WHERE lower(email)=?", (int(is_active), str(email).strip().lower()))
    conn.commit()
    conn.close()


def update_user_role(email
