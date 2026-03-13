import pytest
from unittest.mock import MagicMock

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_costs.db"
    monkeypatch.setattr("api_cost_tracker.db.DB_PATH", db_file)
    from api_cost_tracker.db import init_db
    init_db()
    return db_file

@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr("api_cost_tracker.router.CACHE_DIR", cache_dir)
    return cache_dir

@pytest.fixture
def sample_record():
    from api_cost_tracker.router import RequestRecord
    return RequestRecord(
        timestamp        = "2026-03-13T10:00:00",
        prompt_preview   = "What is 5 + 3?",
        complexity       = "low",
        model_used       = "claude-haiku-4-5-20251001",
        input_tokens     = 32,
        output_tokens    = 5,
        input_cost       = 0.0000256,
        output_cost      = 0.00002,
        total_cost       = 0.0000456,
        cache_hit        = False,
        response_preview = "8",
    )

@pytest.fixture
def mock_anthropic(mocker):
    mock_client = MagicMock()

    classify_response         = MagicMock()
    classify_response.content = [MagicMock(text="low")]

    main_response             = MagicMock()
    main_response.content     = [MagicMock(text="8")]
    main_response.usage       = MagicMock(input_tokens=32, output_tokens=5)

    mock_client.messages.create.side_effect = [classify_response, main_response]

    mocker.patch("api_cost_tracker.router.anthropic.Anthropic", return_value=mock_client)
    return mock_client
