import pytest
from io import StringIO
from unittest.mock import patch
from api_cost_tracker.cli import main
from api_cost_tracker.tracker import save_record

def run_cli(*args):
    with patch("sys.argv", ["costs", *args]):
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            try:
                main()
            except SystemExit:
                pass
            return mock_out.getvalue()

def test_summary_empty(tmp_db):
    out = run_cli("summary")
    assert "SUMMARY" in out
    assert "Requests" in out

def test_summary_with_data(tmp_db, sample_record):
    save_record(sample_record)
    out = run_cli("summary")
    assert "claude-haiku" in out
    assert "$" in out

def test_summary_with_period(tmp_db, sample_record):
    save_record(sample_record)
    out = run_cli("summary", "--period", "7d")
    assert "last 7d" in out

def test_daily(tmp_db, sample_record):
    save_record(sample_record)
    out = run_cli("daily")
    assert "DATE" in out

def test_top(tmp_db, sample_record):
    save_record(sample_record)
    out = run_cli("top", "--limit", "1")
    assert "most expensive" in out

def test_models(tmp_db, sample_record):
    save_record(sample_record)
    out = run_cli("models")
    assert "claude-haiku" in out

def test_export_csv(tmp_db, sample_record):
    save_record(sample_record)
    out = run_cli("export")
    assert "model_used" in out
    assert "claude-haiku" in out

def test_export_empty(tmp_db):
    out = run_cli("export")
    assert "No records found" in out

def test_clear_confirmed(tmp_db, sample_record, monkeypatch):
    save_record(sample_record)
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    run_cli("clear")
    out = run_cli("summary")
    assert "Requests   : 0" in out

def test_clear_cancelled(tmp_db, sample_record, monkeypatch):
    save_record(sample_record)
    monkeypatch.setattr("builtins.input", lambda _: "no")
    run_cli("clear")
    out = run_cli("summary")
    assert "Requests   : 1" in out
