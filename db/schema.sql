-- ============================================================
-- MarketMind SQLite Schema
-- File: db/marketmind.db
-- ============================================================

PRAGMA journal_mode = WAL;   -- Write-Ahead Logging: faster concurrent reads
PRAGMA foreign_keys = ON;

-- ── Users ────────────────────────────────────────────────────
-- One row per trader. Stores preferred language for dialect routing.
CREATE TABLE IF NOT EXISTS users (
    user_id     TEXT PRIMARY KEY,
    name        TEXT,
    language    TEXT NOT NULL DEFAULT 'pidgin',  -- en | pidgin | yoruba | igbo | hausa
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Transactions ─────────────────────────────────────────────
-- Every single sale or expense the trader logs.
CREATE TABLE IF NOT EXISTS transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL REFERENCES users(user_id),
    type            TEXT NOT NULL CHECK(type IN ('sale', 'expense')),
    item            TEXT NOT NULL,          -- e.g. "tomatoes", "rice"
    amount          REAL NOT NULL,          -- in Naira
    quantity        TEXT,                   -- e.g. "2 mudu", "3 bags" (free text)
    raw_input       TEXT,                   -- original user message (for audit)
    language        TEXT,                   -- language the input was in
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    date            TEXT NOT NULL DEFAULT (date('now'))  -- YYYY-MM-DD for fast grouping
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_date
    ON transactions(user_id, date);

-- ── Daily Summaries ──────────────────────────────────────────
-- Pre-computed per-user per-day totals.
-- Rebuilt automatically after each new transaction (via ledger.py).
-- Used by the QUERY_PROFIT path (no LLM needed) and RAG indexing.
CREATE TABLE IF NOT EXISTS daily_summaries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL REFERENCES users(user_id),
    date            TEXT NOT NULL,
    total_sales     REAL NOT NULL DEFAULT 0,
    total_expenses  REAL NOT NULL DEFAULT 0,
    net_profit      REAL NOT NULL DEFAULT 0,
    top_item        TEXT,                   -- highest revenue item that day
    top_item_amount REAL,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, date)                   -- one summary per user per day
);

CREATE INDEX IF NOT EXISTS idx_summaries_user_date
    ON daily_summaries(user_id, date);
