# db/repository.py
import os
import json
import sqlite3
from datetime import datetime, date


# ==========================================================
# DB PATH (Railway-safe)
# ==========================================================
DB_PATH = os.getenv("DB_PATH", os.path.join("data", "app.db"))

ADMIN_EMAIL = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or ""


# ==========================================================
# INTERNAL HELPERS
# ==========================================================
def _ensure_parent_dir(path: str):
    parent = os.path.dirname(path)
    if parent and parent not in ("/", ".") and not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except Exception:
            pass


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
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
    Minimal schema to prevent Railway failures (no dependency on schema.sql).
    Safe to run repeatedly.
    """
    cur = conn.cursor()

    # USERS
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'Analyst',
            is_active INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # REVIEWS
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            industry TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # KPI INPUTS
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS kpi_inputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            kpi_id TEXT NOT NULL,
            value REAL DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(review_id, kpi_id)
        )
        """
    )

    # KPI SCORES (computed)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            kpi_id TEXT NOT NULL,
            score REAL DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(review_id, kpi_id)
        )
        """
    )

    # EXPORT LOG
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            review_id INTEGER,
            export_type TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # SUBSCRIPTIONS (simple)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            can_export INTEGER DEFAULT 1,
            export_limit_per_day INTEGER DEFAULT 999,
            can_create_review INTEGER DEFAULT 1,
            review_limit INTEGER DEFAULT 999,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()


def _ensure_financial_raw_shape(conn: sqlite3.Connection):
    """
    Fixes Railway mismatch: supports both `payload` and `data_json`.
    """
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS financial_raw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            payload TEXT,
            data_json TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

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


def _ensure_admin_bootstrap(conn: sqlite3.Connection):
    """
    Ensures ADMIN_EMAIL exists and is active Admin (fixes 'pending approval').
    """
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        return

    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE lower(email)=?", (ADMIN_EMAIL,))
    row = cur.fetchone()

    if row:
        cur.execute("UPDATE users SET role='Admin', is_active=1 WHERE id=?", (row["id"],))
    else:
        cur.execute(
            "INSERT INTO users (email, password, role, is_active) VALUES (?, ?, 'Admin', 1)",
            (ADMIN_EMAIL, ADMIN_PASSWORD),
        )

    conn.commit()


# ==========================================================
# CONNECTION
# ==========================================================
def get_connection():
    _ensure_parent_dir(DB_PATH)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass

    _apply_min_schema(conn)
    _ensure_financial_raw_shape(conn)
    _ensure_admin_bootstrap(conn)

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
    email_norm = str(email).strip().lower()
    role_norm = (role or "Analyst").strip()

    # Always activate Admin/CEO
    if role_norm.lower() in ("admin", "ceo"):
        is_active = 1

    # Also activate bootstrap admin
    if ADMIN_EMAIL and email_norm == ADMIN_EMAIL:
        role_norm = "Admin"
        is_active = 1

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (email, password, role, is_active) VALUES (?, ?, ?, ?)",
        (email_norm, str(password), role_norm, int(is_active)),
    )
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid


def set_user_active(email: str, is_active: int = 1):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_active=? WHERE lower(email)=?", (int(is_active), str(email).strip().lower()))
    conn.commit()
    conn.close()


def update_user_role(email: str, role: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET role=? WHERE lower(email)=?", (str(role).strip(), str(email).strip().lower()))
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
        (str(company_name).strip(), str(industry).strip()),
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
    return rows


def get_review_by_id(review_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, company_name, industry, created_at FROM reviews WHERE id=?", (int(review_id),))
    row = cur.fetchone()
    conn.close()
    return row


# ==========================================================
# KPI INPUTS
# ==========================================================
def get_kpi_inputs(review_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT kpi_id, value FROM kpi_inputs WHERE review_id=?", (int(review_id),))
    rows = cur.fetchall()
    conn.close()
    return {r["kpi_id"]: r["value"] for r in rows}


def save_kpi_value(review_id: int, kpi_id: str, value):
    conn = get_conn()
    cur = conn.cursor()

    try:
        val = float(value)
    except Exception:
        val = 0.0

    cur.execute(
        """
        INSERT INTO kpi_inputs (review_id, kpi_id, value, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(review_id, kpi_id) DO UPDATE SET
            value=excluded.value,
            updated_at=CURRENT_TIMESTAMP
        """,
        (int(review_id), str(kpi_id), val),
    )
    conn.commit()
    conn.close()


def save_financial_kpis(review_id: int, metrics: dict):
    """
    Writes computed KPI values into kpi_inputs (so Data Input displays them).
    """
    metrics = metrics or {}
    for kpi_id, val in metrics.items():
        save_kpi_value(review_id, kpi_id, val)


# ==========================================================
# FINANCIAL RAW (reload persistence)
# ==========================================================
def save_financial_raw(review_id: int, data: dict):
    conn = get_conn()
    _ensure_financial_raw_shape(conn)
    cur = conn.cursor()

    payload = json.dumps(data or {}, ensure_ascii=False)

    # keep 1 latest row per review
    cur.execute("DELETE FROM financial_raw WHERE review_id=?", (int(review_id),))
    cur.execute(
        "INSERT INTO financial_raw (review_id, payload, data_json) VALUES (?, ?, ?)",
        (int(review_id), payload, payload),
    )

    conn.commit()
    conn.close()


def load_financial_raw(review_id: int):
    conn = get_conn()
    _ensure_financial_raw_shape(conn)
    cur = conn.cursor()

    # Try payload first, then data_json
    if _column_exists(conn, "financial_raw", "payload"):
        cur.execute(
            """
            SELECT payload
            FROM financial_raw
            WHERE review_id=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(review_id),),
        )
        row = cur.fetchone()
        if row and row["payload"]:
            conn.close()
            try:
                return json.loads(row["payload"])
            except Exception:
                return None

    cur.execute(
        """
        SELECT data_json
        FROM financial_raw
        WHERE review_id=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(review_id),),
    )
    row = cur.fetchone()
    conn.close()

    if not row or not row["data_json"]:
        return None

    try:
        return json.loads(row["data_json"])
    except Exception:
        return None


# ==========================================================
# SCORES (for Scoring + Benchmarking)
# ==========================================================
def save_scores(review_id: int, score_map: dict):
    """
    score_map: {kpi_id: score}
    """
    score_map = score_map or {}
    conn = get_conn()
    cur = conn.cursor()

    for kpi_id, sc in score_map.items():
        try:
            scf = float(sc)
        except Exception:
            scf = 0.0

        cur.execute(
            """
            INSERT INTO scores (review_id, kpi_id, score, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(review_id, kpi_id) DO UPDATE SET
                score=excluded.score,
                updated_at=CURRENT_TIMESTAMP
            """,
            (int(review_id), str(kpi_id), scf),
        )

    conn.commit()
    conn.close()


def get_scores(review_id: int):
    """
    Returns dict(kpi_id -> score)
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT kpi_id, score FROM scores WHERE review_id=?", (int(review_id),))
    rows = cur.fetchall()
    conn.close()
    return {r["kpi_id"]: r["score"] for r in rows}


# ==========================================================
# SUBSCRIPTIONS (used by core/billing_engine.py)
# ==========================================================
def get_user_subscription(user_id: int):
    """
    Returns a Row; if missing, auto-creates a generous default.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM subscriptions WHERE user_id=?", (int(user_id),))
    row = cur.fetchone()

    if row:
        conn.close()
        return row

    # Create default
    cur.execute(
        """
        INSERT INTO subscriptions (user_id, can_export, export_limit_per_day, can_create_review, review_limit)
        VALUES (?, 1, 999, 1, 999)
        """,
        (int(user_id),),
    )
    conn.commit()

    cur.execute("SELECT * FROM subscriptions WHERE user_id=?", (int(user_id),))
    row = cur.fetchone()
    conn.close()
    return row


def record_export(user_id: int, review_id: int | None, export_type: str = "board_report"):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO exports (user_id, review_id, export_type) VALUES (?, ?, ?)",
        (int(user_id), int(review_id) if review_id is not None else None, str(export_type)),
    )
    conn.commit()
    conn.close()


def count_exports_today(user_id: int):
    today = date.today().isoformat()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM exports
        WHERE user_id=?
          AND date(created_at)=?
        """,
        (int(user_id), today),
    )
    row = cur.fetchone()
    conn.close()
    return int(row["n"] if row else 0)
