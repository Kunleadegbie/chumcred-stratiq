import sqlite3
import os
import json
from datetime import datetime


# ==========================================================
# PATHS
# ==========================================================

# Project root (…/db/repository.py -> …/)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Prefer Railway volume if available
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "stratiq.db")
VOLUME_DB_PATH = "/data/stratiq.db"

DB_PATH = os.environ.get("STRATIQ_DB_PATH") or (VOLUME_DB_PATH if os.path.exists("/data") else DEFAULT_DB_PATH)

# Try multiple schema locations (Railway paths differ depending on deploy layout)
SCHEMA_CANDIDATES = [
    os.environ.get("STRATIQ_SCHEMA_PATH", "").strip(),
    os.path.join(BASE_DIR, "db", "schema.sql"),
    os.path.join(os.path.dirname(__file__), "schema.sql"),
    "/app/db/schema.sql",
    "/data/db/schema.sql",
]
SCHEMA_CANDIDATES = [p for p in SCHEMA_CANDIDATES if p]


# ==========================================================
# INTERNAL HELPERS
# ==========================================================

def _table_exists(conn, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cur.fetchone() is not None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    cur = conn.cursor()
    try:
        cur.execute(f"PRAGMA table_info({table_name})")
        cols = [r[1] for r in cur.fetchall()]  # r[1] = name
        return column_name in cols
    except Exception:
        return False


def _apply_schema_if_available(conn):
    schema_path = None
    for p in SCHEMA_CANDIDATES:
        if p and os.path.exists(p):
            schema_path = p
            break

    # If schema exists, use it (your original behavior)
    if schema_path:
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
            conn.commit()
        return True

    # If schema file not found, create minimal required tables safely
    cur = conn.cursor()

    # users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            full_name TEXT,
            password_hash TEXT,
            role TEXT DEFAULT 'Pending',
            is_active INTEGER DEFAULT 0
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
            raw_value REAL,
            score REAL,
            pillar TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # subscriptions (if your app uses it)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan TEXT,
            start_date TEXT,
            end_date TEXT,
            max_reviews INTEGER,
            max_exports INTEGER,
            used_reviews INTEGER DEFAULT 0,
            used_exports INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )
    """)

    # financial_raw (for Financial Analyzer persistence)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS financial_raw (
            review_id INTEGER PRIMARY KEY,
            data_json TEXT,
            updated_at TEXT
        )
    """)

    conn.commit()
    return False


def _ensure_financial_raw_shape(conn):
    # Ensure table exists
    if not _table_exists(conn, "financial_raw"):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS financial_raw (
                review_id INTEGER PRIMARY KEY,
                data_json TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()

    # Ensure data_json column exists (older deployments may differ)
    if not _column_exists(conn, "financial_raw", "data_json"):
        try:
            conn.execute("ALTER TABLE financial_raw ADD COLUMN data_json TEXT")
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
# CONNECTION + AUTO INIT
# ==========================================================

def get_connection():
    # Ensure parent folder exists (for custom DB path)
    parent = os.path.dirname(DB_PATH)
    if parent and parent != "/" and not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # If users table missing, initialize schema safely
    if not _table_exists(conn, "users"):
        _apply_schema_if_available(conn)

    # Always ensure these exist (prevents Railway “blank after restart” issues)
    _apply_schema_if_available(conn) if not _table_exists(conn, "reviews") else None
    _ensure_financial_raw_shape(conn)

    return conn


# Alias (for backward compatibility)
def get_conn():
    return get_connection()


# ==========================================================
# REVIEWS
# ==========================================================

def create_review(company_name, industry):
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

    rows = conn.execute("""
        SELECT id, company_name, industry, created_at
        FROM reviews
        ORDER BY id DESC
    """).fetchall()

    conn.close()
    return rows


def get_review_by_id(review_id):
    conn = get_conn()

    row = conn.execute("""
        SELECT id, company_name, industry, created_at
        FROM reviews
        WHERE id=?
    """, (review_id,)).fetchone()

    conn.close()
    return row


# ==========================================================
# KPI INPUTS
# ==========================================================

def save_kpi_value(review_id, kpi_id, value):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM kpi_inputs
        WHERE review_id=? AND kpi_id=?
    """, (review_id, kpi_id))

    cur.execute("""
        INSERT INTO kpi_inputs (review_id, kpi_id, value)
        VALUES (?, ?, ?)
    """, (review_id, kpi_id, float(value)))

    conn.commit()
    conn.close()


def get_kpi_inputs(review_id):
    conn = get_conn()

    rows = conn.execute("""
        SELECT kpi_id, value
        FROM kpi_inputs
        WHERE review_id=?
    """, (review_id,)).fetchall()

    conn.close()

    # sqlite Row -> dict
    out = {}
    for r in rows:
        out[str(r["kpi_id"])] = r["value"]
    return out


# ==========================================================
# SCORES
# ==========================================================

def save_scores(review_id, results):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM scores WHERE review_id=?", (review_id,))

    for r in results:
        cur.execute("""
            INSERT INTO scores
            (review_id, kpi_id, raw_value, score, pillar)
            VALUES (?, ?, ?, ?, ?)
        """, (
            review_id,
            r["kpi_id"],
            r["value"],
            r["score"],
            r["pillar"]
        ))

    conn.commit()
    conn.close()


def get_scores(review_id):
    conn = get_conn()

    rows = conn.execute("""
        SELECT kpi_id, raw_value, score, pillar
        FROM scores
        WHERE review_id=?
    """, (review_id,)).fetchall()

    conn.close()
    return rows


# ==========================================================
# USERS
# ==========================================================

def create_user(email, name, password_hash, role="Pending", is_active=0):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users (
            email,
            full_name,
            password_hash,
            role,
            is_active
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        email,
        name,
        password_hash,
        role,
        is_active
    ))

    conn.commit()
    conn.close()


def get_user_by_email(email):
    conn = get_conn()

    row = conn.execute("""
        SELECT id, email, full_name, password_hash, role, is_active
        FROM users
        WHERE email=?
    """, (email,)).fetchone()

    conn.close()
    return row


def get_all_users():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, email, full_name, role, is_active
        FROM users
        ORDER BY id
    """)

    rows = cur.fetchall()
    conn.close()

    users = []
    for r in rows:
        users.append({
            "id": r["id"],
            "email": r["email"],
            "full_name": r["full_name"],
            "role": r["role"],
            "is_active": r["is_active"]
        })
    return users


def update_user_role(user_id, role):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET role=?
        WHERE id=?
    """, (role, user_id))

    conn.commit()
    conn.close()


def activate_user(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET is_active=1
        WHERE id=?
    """, (user_id,))

    conn.commit()
    conn.close()


# ==========================================================
# SUBSCRIPTIONS
# ==========================================================

def get_user_subscription(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM subscriptions
        WHERE user_id=?
        AND is_active=1
        LIMIT 1
    """, (user_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return dict(row)


def create_subscription(user_id, plan, start_date, end_date, max_reviews, max_exports):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO subscriptions (
            user_id,
            plan,
            start_date,
            end_date,
            max_reviews,
            max_exports,
            used_reviews,
            used_exports,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, 0, 0, 1)
    """, (
        user_id,
        plan,
        start_date,
        end_date,
        max_reviews,
        max_exports
    ))

    conn.commit()
    conn.close()


def increment_reviews(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE subscriptions
        SET used_reviews = used_reviews + 1
        WHERE user_id=?
    """, (user_id,))

    conn.commit()
    conn.close()


def increment_exports(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE subscriptions
        SET used_exports = used_exports + 1
        WHERE user_id=?
    """, (user_id,))

    conn.commit()
    conn.close()


# ==========================================================
# FINANCIAL RAW (PERSIST INPUTS)
# ==========================================================

def save_financial_raw(review_id, data: dict):
    conn = get_conn()
    _ensure_financial_raw_shape(conn)

    cur = conn.cursor()
    cur.execute("""
        INSERT INTO financial_raw (review_id, data_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(review_id) DO UPDATE SET
            data_json=excluded.data_json,
            updated_at=excluded.updated_at
    """, (
        int(review_id),
        json.dumps(data, ensure_ascii=False),
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()


def load_financial_raw(review_id):
    conn = get_conn()
    _ensure_financial_raw_shape(conn)

    cur = conn.cursor()
    cur.execute("""
        SELECT data_json
        FROM financial_raw
        WHERE review_id=?
        LIMIT 1
    """, (int(review_id),))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    try:
        payload = row["data_json"]
        if not payload:
            return None
        return json.loads(payload)
    except Exception:
        return None


# ==========================================================
# FINANCIAL KPI SAVE (USES KPI_INPUTS)
# ==========================================================

def save_financial_kpis(review_id, metrics: dict):
    """
    Saves computed KPIs into kpi_inputs so they show up on Data Input page.
    metrics example:
    {
        "FIN_REV_GROWTH": 12.5,
        "FIN_PROFIT_MARGIN": 24.3,
    }
    """
    for kpi_id, value in (metrics or {}).items():
        save_kpi_value(review_id, kpi_id, float(value))
