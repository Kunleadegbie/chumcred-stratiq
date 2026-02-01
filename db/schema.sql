-- Reviews (one per company assessment)
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    industry TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- KPI values entered by user
CREATE TABLE IF NOT EXISTS kpi_inputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL,
    kpi_id TEXT NOT NULL,
    value REAL NOT NULL,
    FOREIGN KEY (review_id) REFERENCES reviews(id)
);

-- Scoring results
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL,
    kpi_id TEXT NOT NULL,
    raw_value REAL,
    score INTEGER,
    pillar TEXT,
    FOREIGN KEY (review_id) REFERENCES reviews(id)
);


-- ----------------------------
-- Users (Internal Auth)
-- ----------------------------
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL, -- CEO | Analyst | Admin
    is_active INTEGER DEFAULT 1
);


-- ----------------------------
-- Subscriptions
-- ----------------------------

CREATE TABLE IF NOT EXISTS subscriptions (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    plan TEXT NOT NULL,  -- Starter | Pro | Enterprise

    start_date DATE,

    end_date DATE,

    is_active INTEGER DEFAULT 1,

    max_reviews INTEGER,

    max_exports INTEGER,

    FOREIGN KEY (user_id) REFERENCES users(id)
);


CREATE TABLE IF NOT EXISTS financial_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER,
    metric TEXT,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



