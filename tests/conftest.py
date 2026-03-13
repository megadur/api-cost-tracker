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
        provider         = "gemini",
        model_used       = "gemini-2.0-flash",
        input_tokens     = 32,
        output_tokens    = 5,
        input_cost       = 0.0,
        output_cost      = 0.0,
        total_cost       = 0.0,
        cache_hit        = False,
        response_preview = "8",
    )

@pytest.fixture
def mock_gemini(mocker):
    """Mock Gemini for classifier + main call."""
    mock_model    = MagicMock()
    classify_resp = MagicMock(text="low")
    main_resp     = MagicMock(
        text="8",
        usage_metadata=MagicMock(prompt_token_count=32, candidates_token_count=5)
    )
    mock_model.generate_content.side_effect = [classify_resp, main_resp]

    mock_genai = mocker.patch("api_cost_tracker.router.genai")
    mock_genai.GenerativeModel.return_value = mock_model
    mocker.patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    return mock_model

@pytest.fixture
def mock_anthropic(mocker):
    mock_client               = MagicMock()
    main_response             = MagicMock()
    main_response.content     = [MagicMock(text="complex answer")]
    main_response.usage       = MagicMock(input_tokens=100, output_tokens=50)
    mock_client.messages.create.return_value = main_response
    mocker.patch("api_cost_tracker.router.anthropic.Anthropic", return_value=mock_client)
    return mock_client
