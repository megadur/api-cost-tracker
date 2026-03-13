from api_cost_tracker.db import get_conn, init_db

def test_init_db_creates_table(tmp_db):
    with get_conn() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    assert any(t["name"] == "requests" for t in tables)

def test_init_db_is_idempotent(tmp_db):
    init_db()
    init_db()

def test_db_file_created(tmp_db):
    assert tmp_db.exists()

def test_insert_and_query(tmp_db):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO requests (timestamp, model_used, total_cost, cache_hit)
            VALUES ('2026-03-13T10:00:00', 'claude-haiku-4-5-20251001', 0.001, 0)
        """)
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM requests").fetchone()
    assert row["model_used"] == "claude-haiku-4-5-20251001"
    assert row["total_cost"] == 0.001
