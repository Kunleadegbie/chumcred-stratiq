import os
import json
import sqlite3
from datetime import datetime

# ==========================================================
# DB LOCATION (Railway-safe)
# ==========================================================

# If you mounted a Railway Volume at /data, this keeps the DB persistent.
# Otherwise it falls back to a local file.
DB_PATH = os.getenv("SQLITE_DB_PATH", "/data/stratiq.db")


# ==========================================================
# INTERNAL HELPERS
# ==========================================================

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
        cols = [r[1] for r in cur.fetchall()]
        return column_name in cols
    except Exception:
        return False


def _apply_schema_if_available(conn: sqlite3.Connection) -> bool:
    """
    Tries to apply db/schema.sql if present.
    If not present (common in Railway deployments), it creates a minimal schema
    so the app still works.
    Returns True if schema.sql was applied, otherwise False.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(base_dir, "schema.sql")

    if os.path.exists(schema_path):
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                sql = f.read()
            conn.executescript(sql)
            conn.commit()
            return True
        except Exception:
            # If schema.sql exists but fails, fall through to minimal schema
            pass

    # ---- Minimal schema fallback (Railway-safe) ----
    cur = conn.cursor()

    # users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'User',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # subscriptions (for billing / export gating)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan TEXT DEFAULT 'free',
            can_export INTEGER DEFAULT 0,
            export_limit INTEGER DEFAULT 0,
            exports_used INTEGER DEFAULT 0,
            can_create_review INTEGER DEFAULT 1,
            review_limit INTEGER DEFAULT 999,
            reviews_created INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # reviews
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            industry TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # kpi_inputs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kpi_inputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER,
            kpi_id TEXT,
            value REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # scores
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER,
            kpi_id TEXT,
            score REAL,
            pillar TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # export_logs (optional but used in some builds)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS export_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER,
            user_id INTEGER,
            exported_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # financial_raw (for Financial Analyzer persistence)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS financial_raw (
            review_id INTEGER PRIMARY KEY,
            data_json TEXT,
            payload TEXT,
            updated_at TEXT
        )
    """)

    conn.commit()
    return False


def _ensure_financial_raw_shape(conn: sqlite3.Connection):
    """
    Ensures the financial_raw table and the expected columns exist.
    We keep BOTH 'data_json' and 'payload' columns for backward-compat
    because earlier versions referenced 'payload' and caused Railway errors.
    """
    if not _table_exists(conn, "financial_raw"):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS financial_raw (
                review_id INTEGER PRIMARY KEY,
                data_json TEXT,
                payload TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()

    if not _column_exists(conn, "financial_raw", "data_json"):
        try:
            conn.execute("ALTER TABLE financial_raw ADD COLUMN data_json TEXT")
            conn.commit()
        except Exception:
            pass

    if not _column_exists(conn, "financial_raw", "payload"):
        try:
            conn.execute("ALTER TABLE financial_raw ADD COLUMN payload TEXT")
            conn.commit()
        except Exception:
            pass

    if not _column_exists(conn, "financial_raw", "updated_at"):
        try:
            conn.execute("ALTER TABLE financial_raw ADD COLUMN updated_at TEXT")
            conn.commit()
        except Exception:
            pass


# ==========================================================
# CONNECTION (AUTO INIT)
# ==========================================================

def get_connection():
    # Ensure parent folder exists
    parent = os.path.dirname(DB_PATH)
    if parent and parent != "/" and not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Ensure schema exists
    if not _table_exists(conn, "users"):
        _apply_schema_if_available(conn)
    else:
        # still ensure other tables exist
        _apply_schema_if_available(conn)

    _ensure_financial_raw_shape(conn)

    return conn


# Backward-compatible alias used across your codebase
def get_conn():
    return get_connection()


# ==========================================================
# USERS / AUTH
# ==========================================================

def create_user(name: str, email: str, password: str, role: str = "User"):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
        (name, email, password, role)
    )
    conn.commit()
    conn.close()


def get_user_by_email(email: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email=?", (email,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def authenticate_user(email: str, password: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, password)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ==========================================================
# SUBSCRIPTIONS / BILLING SUPPORT
# ==========================================================

def get_user_subscription(user_id: int):
    """
    Returns a dict subscription row, or a safe default if none exists.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM subscriptions WHERE user_id=?", (int(user_id),))
    row = cur.fetchone()

    if not row:
        # Safe default
        sub = {
            "plan": "free",
            "can_export": 0,
            "export_limit": 0,
            "exports_used": 0,
            "can_create_review": 1,
            "review_limit": 999,
            "reviews_created": 0
        }
        conn.close()
        return sub

    conn.close()
    return dict(row)


def increment_exports_used(user_id: int):
    conn = get_conn()
    cur = conn.cursor()

    # Ensure row exists
    cur.execute("SELECT id, exports_used FROM subscriptions WHERE user_id=?", (int(user_id),))
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO subscriptions (user_id, exports_used) VALUES (?, ?)",
            (int(user_id), 1)
        )
    else:
        cur.execute(
            "UPDATE subscriptions SET exports_used = COALESCE(exports_used, 0) + 1, updated_at=? WHERE user_id=?",
            (datetime.utcnow().isoformat(), int(user_id))
        )

    conn.commit()
    conn.close()


def increment_reviews_created(user_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, reviews_created FROM subscriptions WHERE user_id=?", (int(user_id),))
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO subscriptions (user_id, reviews_created) VALUES (?, ?)",
            (int(user_id), 1)
        )
    else:
        cur.execute(
            "UPDATE subscriptions SET reviews_created = COALESCE(reviews_created, 0) + 1, updated_at=? WHERE user_id=?",
            (datetime.utcnow().isoformat(), int(user_id))
        )

    conn.commit()
    conn.close()


# ==========================================================
# REVIEWS
# ==========================================================

def create_review(company_name: str, industry: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reviews (company_name, industry) VALUES (?, ?)",
        (company_name, industry)
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def get_reviews():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, company_name, industry, created_at FROM reviews ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [tuple(r) for r in rows] if rows else []


def get_review_by_id(review_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, company_name, industry, created_at FROM reviews WHERE id=?", (int(review_id),))
    row = cur.fetchone()
    conn.close()
    return tuple(row) if row else None


# ==========================================================
# KPI INPUTS
# ==========================================================

def save_kpi_value(review_id: int, kpi_id: str, value: float):
    conn = get_conn()
    cur = conn.cursor()

    # Remove old record
    cur.execute(
        "DELETE FROM kpi_inputs WHERE review_id=? AND kpi_id=?",
        (int(review_id), str(kpi_id))
    )

    # Insert new
    cur.execute(
        "INSERT INTO kpi_inputs (review_id, kpi_id, value) VALUES (?, ?, ?)",
        (int(review_id), str(kpi_id), float(value) if value is not None else 0.0)
    )

    conn.commit()
    conn.close()


def get_kpi_inputs(review_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT kpi_id, value FROM kpi_inputs WHERE review_id=?", (int(review_id),))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return {}
    return {r["kpi_id"]: r["value"] for r in rows}


# ==========================================================
# SCORES
# ==========================================================

def save_scores(review_id: int, score_rows):
    """
    score_rows: list of dicts: {kpi_id, score, pillar}
    """
    conn = get_conn()
    cur = conn.cursor()

    # remove old
    cur.execute("DELETE FROM scores WHERE review_id=?", (int(review_id),))

    for r in (score_rows or []):
        cur.execute(
            "INSERT INTO scores (review_id, kpi_id, score, pillar) VALUES (?, ?, ?, ?)",
            (int(review_id), str(r.get("kpi_id")), float(r.get("score") or 0.0), str(r.get("pillar") or ""))
        )

    conn.commit()
    conn.close()


def get_scores(review_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT kpi_id, score, pillar FROM scores WHERE review_id=?", (int(review_id),))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return []
    return [dict(r) for r in rows]


# ==========================================================
# FINANCIAL ANALYZER PERSISTENCE
# ==========================================================

def save_financial_raw(review_id: int, data: dict):
    """
    Saves Financial Analyzer raw inputs for reload/navigation persistence.
    """
    conn = get_conn()
    _ensure_financial_raw_shape(conn)
    cur = conn.cursor()

    blob = json.dumps(data or {}, ensure_ascii=False)

    # Upsert (review_id is PRIMARY KEY)
    cur.execute("""
        INSERT INTO financial_raw (review_id, data_json, payload, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(review_id) DO UPDATE SET
            data_json=excluded.data_json,
            payload=excluded.payload,
            updated_at=excluded.updated_at
    """, (int(review_id), blob, blob, datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()


def load_financial_raw(review_id: int):
    """
    Loads Financial Analyzer raw inputs for a review.
    Compatible with both 'data_json' and legacy 'payload'.
    """
    conn = get_conn()
    _ensure_financial_raw_shape(conn)
    cur = conn.cursor()

    # Prefer data_json, fallback to payload
    cur.execute("SELECT data_json, payload FROM financial_raw WHERE review_id=?", (int(review_id),))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    raw = row["data_json"] if row["data_json"] else row["payload"]
    if not raw:
        return None

    try:
        return json.loads(raw)
    except Exception:
        return None


def save_financial_kpis(review_id: int, metrics: dict):
    """
    Saves calculated KPIs into kpi_inputs so Data Input page can show them.
    """
    metrics = metrics or {}
    for kpi_id, value in metrics.items():
        save_kpi_value(review_id, str(kpi_id), float(value) if value is not None else 0.0)
