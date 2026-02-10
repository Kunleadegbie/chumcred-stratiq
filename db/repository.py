"""
db/repository.py

SQLite persistence layer used across the app.

Goals:
• Work reliably both locally and on Railway.
• Avoid schema drift errors (e.g., missing columns) by ensuring tables/columns.
• Provide ALL functions that other modules import (login, reviews, KPI input,
  scoring, benchmarking, exports, financial analyzer persistence).

Notes:
• By default we use /data/app.db when the /data directory is writable (Railway
  persistent volume). Otherwise we fall back to ./data/app.db.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ==========================================================
# DATABASE PATH (Railway-friendly)
# ==========================================================

def _choose_db_path() -> Path:
    """
    Prefer /data (Railway volume) if writable; otherwise fall back to project ./data.
    """
    candidates = [
        Path("/data/app.db"),
        Path.cwd() / "data" / "app.db",
    ]
    for p in candidates:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            # Try a tiny write test on the directory
            testfile = p.parent / ".write_test"
            testfile.write_text("ok", encoding="utf-8")
            testfile.unlink(missing_ok=True)
            return p
        except Exception:
            continue
    # Final fallback (current dir)
    return Path.cwd() / "app.db"


DB_PATH = _choose_db_path()


# ==========================================================
# SCHEMA (inline, avoids external schema.sql path issues)
# ==========================================================

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    password_hash TEXT,
    role TEXT DEFAULT 'User',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    industry TEXT,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS kpi_inputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL,
    kpi_id TEXT NOT NULL,
    value REAL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(review_id, kpi_id)
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL,
    scores_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS export_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT NOT NULL,
    review_id INTEGER NOT NULL,
    export_type TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Financial analyzer raw inputs (persisted)
CREATE TABLE IF NOT EXISTS financial_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL UNIQUE,
    data_json TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Optional: AI outputs history (used by some tools)
CREATE TABLE IF NOT EXISTS ai_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT,
    review_id INTEGER,
    tool TEXT,
    prompt TEXT,
    output TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# Backwards-compatible alias (some older modules import get_connection)
# Backwards-compatible alias (some older modules import get_connection)
def get_connection() -> sqlite3.Connection:  # pragma: no cover
    return get_conn()


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()


# Ensure DB is initialized on import
init_db()


# ==========================================================
# USERS (Login / Account)
# ==========================================================

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    if not email:
        return None
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE lower(email)=lower(?) LIMIT 1", (email.strip(),))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(email: str, full_name: str, password_hash: str, role: str = "User") -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (email, full_name, password_hash, role)
        VALUES (?, ?, ?, ?)
        """,
        (email.strip(), (full_name or "").strip(), password_hash, (role or "User").strip()),
    )
    conn.commit()
    user_id = int(cur.lastrowid)
    conn.close()
    return user_id


# ==========================================================
# REVIEWS
# ==========================================================

def create_review(company_name: str, industry: str, created_by: str = "") -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reviews (company_name, industry, created_by)
        VALUES (?, ?, ?)
        """,
        ((company_name or "").strip(), (industry or "").strip(), (created_by or "").strip()),
    )
    conn.commit()
    rid = int(cur.lastrowid)
    conn.close()
    return rid


def get_reviews() -> List[Tuple[int, str, str]]:
    """
    Returns: [(id, company_name, industry), ...] ordered by newest first
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, company_name, industry
        FROM reviews
        ORDER BY id DESC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return [(int(r["id"]), str(r["company_name"]), str(r["industry"] or "")) for r in rows]


def get_review_by_id(review_id: int) -> Optional[Tuple[int, str, str]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, company_name, industry FROM reviews WHERE id=? LIMIT 1", (int(review_id),))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return (int(row["id"]), str(row["company_name"]), str(row["industry"] or ""))


# ==========================================================
# KPI INPUTS
# ==========================================================

def get_kpi_inputs(review_id: int) -> Dict[str, float]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT kpi_id, value
        FROM kpi_inputs
        WHERE review_id=?
        """,
        (int(review_id),),
    )
    rows = cur.fetchall()
    conn.close()
    out: Dict[str, float] = {}
    for r in rows:
        try:
            out[str(r["kpi_id"])] = float(r["value"])
        except Exception:
            out[str(r["kpi_id"])] = 0.0
    return out


def save_kpi_value(review_id: int, kpi_id: str, value: float) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO kpi_inputs (review_id, kpi_id, value)
        VALUES (?, ?, ?)
        ON CONFLICT(review_id, kpi_id)
        DO UPDATE SET value=excluded.value
        """,
        (int(review_id), str(kpi_id), float(value) if value is not None else 0.0),
    )
    conn.commit()
    conn.close()


# ==========================================================
# SCORING PERSISTENCE
# ==========================================================

def save_scores(review_id: int, scores: Dict[str, Dict[str, Any]]) -> None:
    """
    Stores one JSON blob per scoring run. Latest is used by get_scores().
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO scores (review_id, scores_json)
        VALUES (?, ?)
        """,
        (int(review_id), json.dumps(scores or {}, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def get_scores(review_id: int) -> Dict[str, Dict[str, Any]]:
    """
    Returns latest scores_json for a review.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT scores_json
        FROM scores
        WHERE review_id=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(review_id),),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return {}
    try:
        return json.loads(row["scores_json"] or "{}")
    except Exception:
        return {}


# ==========================================================
# FINANCIAL ANALYZER RAW INPUTS (persist across reloads)
# ==========================================================

def _ensure_financial_raw_shape(conn: sqlite3.Connection) -> None:
    """
    Helps avoid schema drift errors when deploying to an environment
    with an older DB file.
    """
    cur = conn.cursor()
    # Make sure table exists (already in SCHEMA_SQL, but keep defensive)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS financial_raw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL UNIQUE,
            data_json TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Ensure required column exists
    cur.execute("PRAGMA table_info(financial_raw)")
    cols = [row[1] for row in cur.fetchall()]  # column name at index 1
    if "data_json" not in cols:
        cur.execute("ALTER TABLE financial_raw ADD COLUMN data_json TEXT")
    conn.commit()


def save_financial_raw(review_id: int, data: Dict[str, Any]) -> None:
    conn = get_conn()
    _ensure_financial_raw_shape(conn)
    cur = conn.cursor()
    payload = json.dumps(data or {}, ensure_ascii=False)
    cur.execute(
        """
        INSERT INTO financial_raw (review_id, data_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(review_id)
        DO UPDATE SET data_json=excluded.data_json, updated_at=CURRENT_TIMESTAMP
        """,
        (int(review_id), payload),
    )
    conn.commit()
    conn.close()


def load_financial_raw(review_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    _ensure_financial_raw_shape(conn)
    cur = conn.cursor()
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
    if not row:
        return None
    try:
        return json.loads(row["data_json"] or "{}")
    except Exception:
        return None


def save_financial_kpis(review_id: int, metrics: Dict[str, Any]) -> None:
    """
    Writes computed KPIs directly into kpi_inputs so they show up
    on the KPI Data Input page.
    """
    metrics = metrics or {}
    for kpi_id, value in metrics.items():
        save_kpi_value(review_id, str(kpi_id), float(value) if value is not None else 0.0)


# ==========================================================
# AI OUTPUTS (optional)
# ==========================================================

def save_ai_output(user_email: str, review_id: int, tool: str, prompt: str, output: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ai_outputs (user_email, review_id, tool, prompt, output)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            (user_email or "").strip(),
            int(review_id),
            (tool or "").strip(),
            (prompt or ""),
            (output or ""),
        ),
    )
    conn.commit()
    conn.close()


# ==========================================================
# EXPORT LOG (used by billing/export guards)
# ==========================================================

def get_export_count(user_email: str, days: int = 30) -> int:
    """
    Returns how many exports the user has made within the last N days.
    """
    conn = get_conn()
    cur = conn.cursor()

    # SQLite date arithmetic
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM export_log
        WHERE lower(user_email)=lower(?)
          AND datetime(created_at) >= datetime('now', ?)
        """,
        (user_email.strip(), f"-{int(days)} days"),
    )
    row = cur.fetchone()
    conn.close()
    try:
        return int(row["c"]) if row else 0
    except Exception:
        return 0


def record_export(user_email: str, review_id: int, export_type: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO export_log (user_email, review_id, export_type)
        VALUES (?, ?, ?)
        """,
        (user_email.strip(), int(review_id), (export_type or "report").strip()),
    )
    conn.commit()
    conn.close()
