"""
MarketMind — SQLite Ledger Helpers
db/ledger.py

Handles all reads and writes to the local SQLite database.
The QUERY_PROFIT path calls get_today_summary() directly —
no LLM involved, response in <50ms.
"""

import sqlite3
import os
from datetime import date, datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "./db/marketmind.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


# ── Connection ────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Return a WAL-mode connection with row_factory for dict-like rows."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables from schema.sql if they don't exist yet."""
    conn = get_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.close()
    print(f"[DB] Initialised at {DB_PATH}")


# ── Users ─────────────────────────────────────────────────────

def get_or_create_user(user_id: str, language: str = "pidgin") -> dict:
    """Return user row, creating it if it doesn't exist."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()

    if not row:
        conn.execute(
            "INSERT INTO users (user_id, language) VALUES (?, ?)",
            (user_id, language),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

    conn.close()
    return dict(row)


def update_user_language(user_id: str, language: str):
    """Update the trader's preferred language."""
    conn = get_connection()
    conn.execute(
        "UPDATE users SET language = ? WHERE user_id = ?",
        (language, user_id),
    )
    conn.commit()
    conn.close()


# ── Transactions ──────────────────────────────────────────────

def log_transaction(
    user_id: str,
    tx_type: str,       # "sale" or "expense"
    item: str,
    amount: float,
    quantity: Optional[str] = None,
    raw_input: Optional[str] = None,
    language: Optional[str] = None,
) -> int:
    """
    Write a transaction and immediately rebuild the daily summary.
    Returns the new transaction ID.
    """
    today = date.today().isoformat()
    conn = get_connection()

    cursor = conn.execute(
        """
        INSERT INTO transactions
            (user_id, type, item, amount, quantity, raw_input, language, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, tx_type, item, amount, quantity, raw_input, language, today),
    )
    tx_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Rebuild today's summary so QUERY_PROFIT is always fresh
    _rebuild_daily_summary(user_id, today)
    return tx_id


# ── Summaries ─────────────────────────────────────────────────

def get_today_summary(user_id: str) -> dict:
    """
    Return today's pre-computed summary.
    Called by QUERY_PROFIT intent — no LLM needed.
    """
    today = date.today().isoformat()
    conn = get_connection()
    row = conn.execute(
        """
        SELECT total_sales, total_expenses, net_profit,
               top_item, top_item_amount
        FROM daily_summaries
        WHERE user_id = ? AND date = ?
        """,
        (user_id, today),
    ).fetchone()
    conn.close()

    if not row:
        return {
            "date": today,
            "total_sales": 0.0,
            "total_expenses": 0.0,
            "net_profit": 0.0,
            "top_item": None,
            "top_item_amount": 0.0,
        }

    return {
        "date": today,
        "total_sales": row["total_sales"],
        "total_expenses": row["total_expenses"],
        "net_profit": row["net_profit"],
        "top_item": row["top_item"],
        "top_item_amount": row["top_item_amount"],
    }


def get_recent_summaries(user_id: str, days: int = 30) -> list[dict]:
    """
    Return the last N daily summaries as plain dicts.
    Used to build RAG context chunks for ADVISORY queries.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT date, total_sales, total_expenses, net_profit,
               top_item, top_item_amount
        FROM daily_summaries
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        (user_id, days),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_item_breakdown(user_id: str, days: int = 7) -> list[dict]:
    """
    Return per-item totals for the last N days.
    Used in ADVISORY prompts for margin analysis.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT item,
               SUM(CASE WHEN type='sale' THEN amount ELSE 0 END)    AS total_sales,
               SUM(CASE WHEN type='expense' THEN amount ELSE 0 END)  AS total_expenses,
               COUNT(*) AS tx_count
        FROM transactions
        WHERE user_id = ?
          AND date >= date('now', ? || ' days')
          AND type IN ('sale', 'expense')
        GROUP BY item
        ORDER BY total_sales DESC
        """,
        (user_id, f"-{days}"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_transactions(user_id: str, limit: int = 50) -> list[dict]:
    """
    Return the most recent transactions for the dashboard.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, type, item, amount, quantity, created_at, date
        FROM transactions
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Internal: Summary Builder ─────────────────────────────────

def _rebuild_daily_summary(user_id: str, target_date: str):
    """
    Recompute and upsert the daily summary for a given date.
    Called internally after every logged transaction.
    """
    conn = get_connection()

    # Aggregate sales and expenses
    agg = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN type='sale' THEN amount ELSE 0 END), 0)    AS sales,
            COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) AS expenses
        FROM transactions
        WHERE user_id = ? AND date = ?
        """,
        (user_id, target_date),
    ).fetchone()

    total_sales = agg["sales"]
    total_expenses = agg["expenses"]
    net_profit = total_sales - total_expenses

    # Find top-selling item
    top = conn.execute(
        """
        SELECT item, SUM(amount) AS total
        FROM transactions
        WHERE user_id = ? AND date = ? AND type = 'sale'
        GROUP BY item
        ORDER BY total DESC
        LIMIT 1
        """,
        (user_id, target_date),
    ).fetchone()

    top_item = top["item"] if top else None
    top_item_amount = top["total"] if top else 0.0

    # Upsert
    conn.execute(
        """
        INSERT INTO daily_summaries
            (user_id, date, total_sales, total_expenses, net_profit,
             top_item, top_item_amount, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, date) DO UPDATE SET
            total_sales     = excluded.total_sales,
            total_expenses  = excluded.total_expenses,
            net_profit      = excluded.net_profit,
            top_item        = excluded.top_item,
            top_item_amount = excluded.top_item_amount,
            updated_at      = excluded.updated_at
        """,
        (
            user_id, target_date, total_sales, total_expenses,
            net_profit, top_item, top_item_amount,
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()
