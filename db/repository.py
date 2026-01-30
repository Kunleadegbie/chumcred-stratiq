import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "app.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    with open(Path(__file__).parent / "schema.sql") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


# ---------------- Reviews ----------------

def create_review(company, industry):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO reviews (company_name, industry) VALUES (?, ?)",
        (company, industry)
    )

    conn.commit()
    review_id = cur.lastrowid
    conn.close()

    return review_id


def get_reviews():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, company_name, industry, created_at FROM reviews ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return rows


# ---------------- KPI Inputs ----------------

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


# ---------------- Scores ----------------

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

def get_review_by_id(review_id):
    conn = get_conn()

    row = conn.execute("""
        SELECT id, company_name, industry, created_at
        FROM reviews
        WHERE id=?
    """, (review_id,)).fetchone()

    conn.close()

    return row

# ---------------- Users ----------------

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


def get_user_by_email(email):
    conn = get_conn()

    row = conn.execute("""
        SELECT id, email, full_name, password_hash, role, is_active
        FROM users
        WHERE email=?
    """, (email,)).fetchone()

    conn.close()

    return row


# ==========================================================
# SUBSCRIPTIONS
# ==========================================================

def get_user_subscription(user_id):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM subscriptions
        WHERE user_id = ?
        AND is_active = 1
        LIMIT 1
    """, (user_id,))

    row = cur.fetchone()

    if not row:
        return None

    cols = [c[0] for c in cur.description]

    return dict(zip(cols, row))


def increment_reviews(user_id):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE subscriptions
        SET used_reviews = used_reviews + 1
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()


def increment_exports(user_id):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE subscriptions
        SET used_exports = used_exports + 1
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()


# ==========================================================
# CREATE SUBSCRIPTION
# ==========================================================

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

# ==================================================
# USERS ADMIN
# ==========================================================

def get_all_users():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, email, full_name, role
        FROM users
    """)

    rows = cur.fetchall()

    users = []

    for r in rows:

        users.append({
            "id": r[0],
            "email": r[1],
            "full_name": r[2],
            "role": r[3]
        })

    return users


def update_user_role(user_id, role):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET role = ?
        WHERE id = ?
    """, (role, user_id))

    conn.commit()

def activate_user(user_id):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET is_active = 1
        WHERE id = ?
    """, (user_id,))

    conn.commit()

# ==================================================
# FINANCIAL KPI SAVE
# ==================================================

def save_financial_kpis(review_id, results):

    conn = get_conn()
    cur = conn.cursor()

    mapping = {

        "rev_cagr": "FIN_REV_GROWTH_YOY",
        "ebitda_margin": "FIN_EBITDA_MARGIN",
        "net_margin": "FIN_NET_MARGIN",
        "roa": "FIN_ROA",
        "roe": "FIN_ROE",
        "current_ratio": "FIN_CURRENT_RATIO",
        "debt_ratio": "FIN_DEBT_RATIO"
    }


    for k, v in mapping.items():

        cur.execute("""
            INSERT INTO kpi_inputs (review_id, kpi_id, value)
            VALUES (?, ?, ?)
        """, (review_id, k, round(v * 100, 2)))


    conn.commit()


