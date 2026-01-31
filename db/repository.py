

import sqlite3
import os


# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DB_PATH = os.path.join(BASE_DIR, "stratiq.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "db", "schema.sql")


# ==========================================================
# CONNECTION + AUTO INIT
# ==========================================================

def get_connection():

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    # Check if users table exists
    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='users'
    """)

    exists = cur.fetchone()

    # If not, load schema
    if not exists:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
            conn.commit()

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
    """, (review_id, kpi_id, value))

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

    return dict(rows)


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

def create_user(
    email,
    name,
    password_hash,
    role="Pending",
    is_active=0
):

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


def create_subscription(
    user_id,
    plan,
    start_date,
    end_date,
    max_reviews,
    max_exports
):

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
# FINANCIAL KPI SAVE
# ==========================================================

def save_financial_kpis(review_id, metrics: dict):

    conn = get_conn()
    cur = conn.cursor()

    # Remove old financial KPIs first
    for kpi_id in metrics.keys():
        cur.execute("""
            DELETE FROM kpi_inputs
            WHERE review_id=? AND kpi_id=?
        """, (review_id, kpi_id))

    # Insert new ones
    for kpi_id, value in metrics.items():

        cur.execute("""
            INSERT INTO kpi_inputs (review_id, kpi_id, value)
            VALUES (?, ?, ?)
        """, (
            review_id,
            kpi_id,
            float(value)
        ))

    conn.commit()
    conn.close()



