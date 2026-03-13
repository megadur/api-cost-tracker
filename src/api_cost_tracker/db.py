import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path.home() / ".api_cost_tracker" / "costs.db"

@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp        TEXT    NOT NULL,
                prompt_preview   TEXT,
                complexity       TEXT,
                model_used       TEXT,
                input_tokens     INTEGER,
                output_tokens    INTEGER,
                input_cost       REAL,
                output_cost      REAL,
                total_cost       REAL,
                cache_hit        INTEGER,
                response_preview TEXT
            )
        """)
