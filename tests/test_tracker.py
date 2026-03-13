import pytest
from api_cost_tracker.tracker import save_record, get_summary, CostTracker

def test_save_and_retrieve(tmp_db, sample_record):
    save_record(sample_record)
    summary = get_summary()
    assert summary["totals"]["requests"]   == 1
    assert summary["totals"]["cache_hits"] == 0

def test_get_summary_totals(tmp_db, sample_record):
    save_record(sample_record)
    save_record(sample_record)
    t = get_summary()["totals"]
    assert t["requests"]      == 2
    assert t["input_tokens"]  == 64
    assert t["output_tokens"] == 10

def test_get_summary_by_model(tmp_db, sample_record):
    save_record(sample_record)
    by_model = get_summary()["by_model"]
    assert len(by_model) == 1
    assert by_model[0]["model_used"] == "claude-haiku-4-5-20251001"

def test_get_summary_empty_db(tmp_db):
    t = get_summary()["totals"]
    assert t["requests"] == 0
    assert t["cost"]     is None

def test_get_summary_with_period(tmp_db, sample_record):
    save_record(sample_record)
    from datetime import datetime, timedelta
    future = (datetime.now() + timedelta(days=1)).isoformat()
    t = get_summary(since=future)["totals"]
    assert t["requests"] == 0

def test_cost_tracker_session(sample_record):
    tracker = CostTracker()
    tracker.add(sample_record)
    tracker.add(sample_record)
    assert tracker.total_cost == pytest.approx(sample_record.total_cost * 2)

def test_cost_tracker_empty():
    tracker = CostTracker()
    assert tracker.total_cost == 0.0
