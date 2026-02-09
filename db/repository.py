# db/repository.py
import os
import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple


# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.environ.get("DB_PATH") or os.path.join(BASE_DIR, "data", "db", "app.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "data", "db", "schema.sql")


# ==========================================================
# CONNECTION
# ==========================================================

def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    _bootstrap_schema_if_needed(conn)
    _ensure_tables_for_runtime(conn)

    return conn


# Backward compatibility (some pages/scripts use get_conn)
def get_conn() -> sqlite3.Connection:
    return get_connection()


def _bootstrap_schema_if_needed(conn: sqlite3.Connection) -> None:
    """
    If schema.sql exists, execute it once (idempotent).
    We do not fail deployment if schema.sql is missing.
    """
    try:
        if os.path.exists(SCHEMA_PATH):
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                sql = f.read().strip()
            if sql:
                conn.executescript(sql)
                conn.commit()
    except Exception:
        # Keep app alive even if schema.sql differs across environments
        pass


def _ensure_tables_for_runtime(conn: sqlite3.Connection) -> None:
    """
    Ensure the minimal tables/columns used by:
    - Data Input
    - Financial Analyzer (reload persistence + KPIs + AI report)
    - Scoring Dashboard (scores + exports)
    """
    cur = conn.cursor()

    # Reviews table (expected shape: id, company_name, industry, created_at)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            industry TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # KPI inputs table (expected by Data Input)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kpi_inputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            kpi_id TEXT NOT NULL,
            value REAL DEFAULT 0.0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Scores table (for Scoring Dashboard / Benchmarking)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            bhi REAL DEFAULT 0.0,
            pillar_json TEXT,
            kpi_json TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Exports table (track export counts)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            review_id INTEGER,
            export_type TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Financial raw persistence table
    # IMPORTANT: We support BOTH old column names (data_json) and new (payload)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS financial_raw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            payload TEXT,
            data_json TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _ensure_column(conn, "financial_raw", "payload", "TEXT")
    _ensure_column(conn, "financial_raw", "data_json", "TEXT")

    # AI Reports (store Financial Analyzer AI Advisor + Alerts)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            report_type TEXT NOT NULL,
            payload TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _ensure_column(conn, "ai_reports", "payload", "TEXT")

    conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, col: str, col_type: str) -> None:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if col not in cols:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except Exception:
            pass


# ==========================================================
# REVIEWS
# ==========================================================

def get_reviews() -> List[Tuple[int, str, str]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, company_name, industry FROM reviews ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [(int(r["id"]), r["company_name"] or "", r["industry"] or "") for r in rows]


def get_review_by_id(review_id: int) -> Optional[Tuple[int, str, str]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, company_name, industry FROM reviews WHERE id=?", (int(review_id),))
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return (int(r["id"]), r["company_name"] or "", r["industry"] or "")


# ==========================================================
# KPI INPUTS
# ==========================================================

def get_kpi_inputs(review_id: int) -> Dict[str, float]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT kpi_id, value
        FROM kpi_inputs
        WHERE review_id=?
    """, (int(review_id),))
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
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM kpi_inputs
        WHERE review_id=? AND kpi_id=?
    """, (int(review_id), str(kpi_id)))

    cur.execute("""
        INSERT INTO kpi_inputs (review_id, kpi_id, value)
        VALUES (?, ?, ?)
    """, (int(review_id), str(kpi_id), float(value) if value is not None else 0.0))

    conn.commit()
    conn.close()


def save_financial_kpis(review_id: int, metrics: Dict[str, Any]) -> None:
    """
    Financial Analyzer writes KPIs into the SAME table used by Data Input (kpi_inputs),
    so the Data Input page can display them immediately.
    """
    metrics = metrics or {}
    conn = get_connection()
    cur = conn.cursor()

    for kpi_id, value in metrics.items():
        cur.execute("""
            DELETE FROM kpi_inputs
            WHERE review_id=? AND kpi_id=?
        """, (int(review_id), str(kpi_id)))

        cur.execute("""
            INSERT INTO kpi_inputs (review_id, kpi_id, value)
            VALUES (?, ?, ?)
        """, (int(review_id), str(kpi_id), float(value) if value is not None else 0.0))

    conn.commit()
    conn.close()


# ==========================================================
# FINANCIAL RAW (RELOAD PERSISTENCE)
# ==========================================================

def save_financial_raw(review_id: int, data: Dict[str, Any]) -> None:
    conn = get_connection()
    cur = conn.cursor()

    payload = json.dumps(data or {}, ensure_ascii=False)

    # keep 1 latest row per review_id
    cur.execute("DELETE FROM financial_raw WHERE review_id=?", (int(review_id),))
    # write into BOTH columns for maximum compatibility
    cur.execute("""
        INSERT INTO financial_raw (review_id, payload, data_json)
        VALUES (?, ?, ?)
    """, (int(review_id), payload, payload))

    conn.commit()
    conn.close()


def load_financial_raw(review_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()

    # Use COALESCE so we don't crash if one column is missing/empty
    cur.execute("""
        SELECT COALESCE(payload, data_json) AS payload
        FROM financial_raw
        WHERE review_id=?
        ORDER BY id DESC
        LIMIT 1
    """, (int(review_id),))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    raw = row["payload"]
    if not raw:
        return None

    try:
        return json.loads(raw)
    except Exception:
        return None


# ==========================================================
# AI REPORTS (FINANCIAL ANALYZER INSIGHTS + ALERTS)
# ==========================================================

def save_ai_report(review_id: int, report_type: str, payload: Dict[str, Any]) -> None:
    conn = get_connection()
    cur = conn.cursor()

    data = json.dumps(payload or {}, ensure_ascii=False)

    cur.execute("""
        DELETE FROM ai_reports
        WHERE review_id=? AND report_type=?
    """, (int(review_id), str(report_type)))

    cur.execute("""
        INSERT INTO ai_reports (review_id, report_type, payload)
        VALUES (?, ?, ?)
    """, (int(review_id), str(report_type), data))

    conn.commit()
    conn.close()


def load_ai_report(review_id: int, report_type: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT payload
        FROM ai_reports
        WHERE review_id=? AND report_type=?
        ORDER BY id DESC
        LIMIT 1
    """, (int(review_id), str(report_type)))

    row = cur.fetchone()
    conn.close()

    if not row or not row["payload"]:
        return None

    try:
        return json.loads(row["payload"])
    except Exception:
        return None


# ==========================================================
# SCORES (SAVE/LOAD)
# ==========================================================

def save_scores(review_id: int, bhi: float, pillar_avgs: Dict[str, float], kpi_scores: Dict[str, float]) -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM scores WHERE review_id=?", (int(review_id),))
    cur.execute("""
        INSERT INTO scores (review_id, bhi, pillar_json, kpi_json)
        VALUES (?, ?, ?, ?)
    """, (
        int(review_id),
        float(bhi) if bhi is not None else 0.0,
        json.dumps(pillar_avgs or {}, ensure_ascii=False),
        json.dumps(kpi_scores or {}, ensure_ascii=False)
    ))

    conn.commit()
    conn.close()


def get_scores(review_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT bhi, pillar_json, kpi_json
        FROM scores
        WHERE review_id=?
        ORDER BY id DESC
        LIMIT 1
    """, (int(review_id),))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    try:
        pillar = json.loads(row["pillar_json"] or "{}")
    except Exception:
        pillar = {}

    try:
        kpis = json.loads(row["kpi_json"] or "{}")
    except Exception:
        kpis = {}

    return {
        "bhi": float(row["bhi"] or 0.0),
        "pillars": pillar,
        "kpis": kpis
    }


# ==========================================================
# EXPORTS
# ==========================================================

def increment_exports(user_id: Optional[int], review_id: Optional[int], export_type: str = "board_report") -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO exports (user_id, review_id, export_type)
        VALUES (?, ?, ?)
    """, (
        int(user_id) if user_id is not None else None,
        int(review_id) if review_id is not None else None,
        str(export_type)
    ))
    conn.commit()
    conn.close()


def get_exports_count(user_id: Optional[int], export_type: str = "board_report") -> int:
    conn = get_connection()
    cur = conn.cursor()
    if user_id is None:
        cur.execute("SELECT COUNT(*) AS c FROM exports WHERE export_type=?", (str(export_type),))
    else:
        cur.execute("""
            SELECT COUNT(*) AS c
            FROM exports
            WHERE export_type=? AND user_id=?
        """, (str(export_type), int(user_id)))
    row = cur.fetchone()
    conn.close()
    return int(row["c"] or 0)
