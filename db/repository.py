# db/repository.py
import os
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime


# ==================================================
# DATABASE PATH + CONNECTION
# ==================================================

BASE_DIR = Path(__file__).resolve().parents[1]  # /app
DEFAULT_DB_PATH = BASE_DIR / "data" / "app.db"

DB_PATH = Path(os.environ.get("DB_PATH", str(DEFAULT_DB_PATH))).resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


# ==================================================
# SCHEMA INIT + SAFE MIGRATIONS
# ==================================================

def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cur.fetchone() is not None


def _get_columns(cur: sqlite3.Cursor, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {row["name"] if isinstance(row, sqlite3.Row) else row[1] for row in cur.fetchall()}


def _ensure_column(cur: sqlite3.Cursor, table: str, col_name: str, col_def_sql: str):
    """
    Adds a column if missing.
    col_def_sql should be: "payload TEXT" etc.
    """
    cols = _get_columns(cur, table)
    if col_name not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def_sql}")


def _init_db(conn: sqlite3.Connection):
    cur = conn.cursor()

    # ---------- users ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'User',
            is_active INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---------- reviews ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            industry TEXT NOT NULL,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---------- kpi_inputs ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kpi_inputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            kpi_id TEXT NOT NULL,
            value REAL DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kpi_inputs_review ON kpi_inputs(review_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kpi_inputs_kpi ON kpi_inputs(kpi_id)")

    # ---------- scores ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            kpi_id TEXT NOT NULL,
            raw_value REAL DEFAULT 0,
            score REAL DEFAULT 0,
            pillar TEXT DEFAULT 'UNKNOWN',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scores_review ON scores(review_id)")

    # ---------- financial_raw (for reload persistence) ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS financial_raw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            payload TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # If Railway already has an old table missing payload, ensure it exists:
    _ensure_column(cur, "financial_raw", "payload", "payload TEXT")

    # ---------- subscriptions ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            plan TEXT DEFAULT 'free',
            export_enabled INTEGER DEFAULT 0,
            export_limit INTEGER DEFAULT 0,
            exports_used INTEGER DEFAULT 0,
            reviews_limit INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()


# ==================================================
# PASSWORD HELPERS (MUST MATCH services/auth.py)
# ==================================================

def _hash_password(password: str) -> str:
    # must match auth.py logic
    salt = os.environ.get("AUTH_SALT", "change_me_salt")
    pepper = os.environ.get("AUTH_PEPPER", "change_me_pepper")
    return hashlib.sha256((password + salt + pepper).encode("utf-8")).hexdigest()


def _looks_like_hash(s: str) -> bool:
    if not isinstance(s, str):
        return False
    if len(s) != 64:
        return False
    try:
        int(s, 16)
        return True
    except Exception:
        return False


# ==================================================
# USERS
# ==================================================

def get_user_by_email(email: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, email, full_name, password_hash, role, is_active
        FROM users
        WHERE lower(email)=lower(?)
        LIMIT 1
    """, (email.strip(),))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    # return tuple to match services/auth.py unpacking
    return (row["id"], row["email"], row["full_name"], row["password_hash"], row["role"], row["is_active"])


def create_user(email: str, password_or_hash: str, full_name: str = "", role: str = "User", is_active: int = 0):
    """
    Accepts either:
    - raw password (we hash it), OR
    - a 64-char hex sha256 hash (stored as-is)
    """
    email = (email or "").strip().lower()
    full_name = (full_name or "").strip()
    role = (role or "User").strip()

    # auto-activate Admin/CEO
    if role.strip().lower() in ("admin", "ceo"):
        is_active = 1

    pw_hash = password_or_hash
    if not _looks_like_hash(password_or_hash):
        pw_hash = _hash_password(password_or_hash)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users (email, full_name, password_hash, role, is_active)
        VALUES (?, ?, ?, ?, ?)
    """, (email, full_name, pw_hash, role, int(is_active)))

    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def approve_user(email: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_active=1 WHERE lower(email)=lower(?)", (email.strip(),))
    conn.commit()
    conn.close()


def update_user_role(email: str, new_role: str):
    conn = get_conn()
    cur = conn.cursor()
    new_role = (new_role or "").strip()
    cur.execute("""
        UPDATE users
        SET role=?
        WHERE lower(email)=lower(?)
    """, (new_role, email.strip()))
    # auto-activate if admin/ceo
    if new_role.lower() in ("admin", "ceo"):
        cur.execute("UPDATE users SET is_active=1 WHERE lower(email)=lower(?)", (email.strip(),))
    conn.commit()
    conn.close()


def get_user_subscription(user_id: int):
    """
    Returns a dict with subscription controls used by billing_engine.
    If missing, returns a safe default.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT plan, export_enabled, export_limit, exports_used, reviews_limit
        FROM subscriptions
        WHERE user_id=?
        LIMIT 1
    """, (int(user_id),))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {
            "plan": "free",
            "export_enabled": 0,
            "export_limit": 0,
            "exports_used": 0,
            "reviews_limit": 0,
        }

    return {
        "plan": row["plan"],
        "export_enabled": int(row["export_enabled"] or 0),
        "export_limit": int(row["export_limit"] or 0),
        "exports_used": int(row["exports_used"] or 0),
        "reviews_limit": int(row["reviews_limit"] or 0),
    }


def increment_exports(user_id: int):
    """
    Increments exports_used in subscriptions; creates a default row if missing.
    """
    user_id = int(user_id)
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM subscriptions WHERE user_id=? LIMIT 1", (user_id,))
    row = cur.fetchone()

    if not row:
        cur.execute("""
            INSERT INTO subscriptions (user_id, plan, export_enabled, export_limit, exports_used, reviews_limit)
            VALUES (?, 'free', 0, 0, 0, 0)
        """, (user_id,))

    cur.execute("""
        UPDATE subscriptions
        SET exports_used = COALESCE(exports_used, 0) + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id=?
    """, (user_id,))

    conn.commit()
    conn.close()


# ==================================================
# REVIEWS
# ==================================================

def create_review(*args, **kwargs):
    """
    Flexible signature to avoid breaking existing page code.

    Supported calls:
      create_review(company_name, industry, created_by)
      create_review(company_name, industry)
      create_review({"company_name":..., "industry":..., "created_by":...})
      create_review(company=..., industry=..., user_id=...)
    """
    company_name = ""
    industry = ""
    created_by = None

    if args and isinstance(args[0], dict):
        d = args[0]
        company_name = d.get("company_name") or d.get("company") or ""
        industry = d.get("industry") or ""
        created_by = d.get("created_by") or d.get("user_id")
    else:
        if len(args) >= 1:
            company_name = args[0] or ""
        if len(args) >= 2:
            industry = args[1] or ""
        if len(args) >= 3:
            created_by = args[2]

    company_name = (kwargs.get("company_name") or kwargs.get("company") or company_name).strip()
    industry = (kwargs.get("industry") or industry).strip()
    created_by = kwargs.get("created_by") or kwargs.get("user_id") or created_by

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reviews (company_name, industry, created_by)
        VALUES (?, ?, ?)
    """, (company_name, industry, int(created_by) if created_by is not None else None))
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def get_reviews():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, company_name, industry, created_by, created_at FROM reviews ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [tuple(r) for r in rows]


def get_review_by_id(review_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, company_name, industry, created_by, created_at FROM reviews WHERE id=? LIMIT 1", (int(review_id),))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return tuple(row)


# ==================================================
# KPI INPUTS
# ==================================================

def get_kpi_inputs(review_id: int) -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT kpi_id, value
        FROM kpi_inputs
        WHERE review_id=?
    """, (int(review_id),))
    rows = cur.fetchall()
    conn.close()
    return {r["kpi_id"]: r["value"] for r in rows} if rows else {}


def save_kpi_value(review_id: int, kpi_id: str, value: float):
    conn = get_conn()
    cur = conn.cursor()

    # delete then insert keeps it simple + consistent
    cur.execute("DELETE FROM kpi_inputs WHERE review_id=? AND kpi_id=?", (int(review_id), str(kpi_id)))
    cur.execute("""
        INSERT INTO kpi_inputs (review_id, kpi_id, value, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (int(review_id), str(kpi_id), float(value) if value is not None else 0.0))

    conn.commit()
    conn.close()


# ==================================================
# FINANCIAL RAW + FINANCIAL KPIs (PERSISTENCE)
# ==================================================

def save_financial_raw(review_id: int, data: dict):
    conn = get_conn()
    cur = conn.cursor()

    payload = json.dumps(data or {}, ensure_ascii=False)

    # single latest per review
    cur.execute("DELETE FROM financial_raw WHERE review_id=?", (int(review_id),))
    cur.execute(
        "INSERT INTO financial_raw (review_id, payload, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (int(review_id), payload)
    )

    conn.commit()
    conn.close()


def load_financial_raw(review_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT payload
        FROM financial_raw
        WHERE review_id=?
        ORDER BY id DESC
        LIMIT 1
    """, (int(review_id),))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    try:
        payload = row["payload"]
        return json.loads(payload) if payload else None
    except Exception:
        return None


def save_financial_kpis(review_id: int, metrics: dict):
    """
    Saves calculated KPIs into kpi_inputs so the Data Input page can display them.
    """
    metrics = metrics or {}
    for kpi_id, value in metrics.items():
        save_kpi_value(review_id, str(kpi_id), float(value) if value is not None else 0.0)


# ==================================================
# SCORES
# ==================================================

def save_scores(review_id: int, results):
    """
    results can be:
      - list[dict] with keys: kpi/kpi_id, raw_value/value, score, pillar
      - list[tuple] (kpi, raw_value, score, pillar)
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM scores WHERE review_id=?", (int(review_id),))

    if not results:
        conn.commit()
        conn.close()
        return

    for item in results:
        if isinstance(item, dict):
            kpi = item.get("kpi_id") or item.get("kpi")
            raw = item.get("raw_value")
            if raw is None:
                raw = item.get("value")
            score = item.get("score", 0)
            pillar = item.get("pillar", "UNKNOWN")
        elif isinstance(item, (list, tuple)) and len(item) >= 4:
            kpi, raw, score, pillar = item[0], item[1], item[2], item[3]
        else:
            continue

        try:
            raw = float(raw) if raw is not None else 0.0
        except Exception:
            raw = 0.0

        try:
            score = float(score) if score is not None else 0.0
        except Exception:
            score = 0.0

        pillar = str(pillar or "UNKNOWN")

        cur.execute("""
            INSERT INTO scores (review_id, kpi_id, raw_value, score, pillar, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (int(review_id), str(kpi), raw, score, pillar))

    conn.commit()
    conn.close()


def get_scores(review_id: int):
    """
    Returns list[dict] for stable downstream rendering.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT kpi_id, raw_value, score, pillar
        FROM scores
        WHERE review_id=?
        ORDER BY kpi_id ASC
    """, (int(review_id),))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return []

    out = []
    for r in rows:
        out.append({
            "kpi": r["kpi_id"],
            "raw_value": r["raw_value"],
            "score": r["score"],
            "pillar": r["pillar"],
        })
    return out
