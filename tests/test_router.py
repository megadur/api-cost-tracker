import pytest
from api_cost_tracker.router import _calculate_cost, MODELS, PRICING

def test_calculate_cost_haiku():
    costs = _calculate_cost("claude-haiku-4-5-20251001", 1_000_000, 1_000_000)
    assert costs["input_cost"]  == pytest.approx(0.80)
    assert costs["output_cost"] == pytest.approx(4.00)
    assert costs["total_cost"]  == pytest.approx(4.80)

def test_calculate_cost_sonnet():
    costs = _calculate_cost("claude-sonnet-4-6", 1_000_000, 1_000_000)
    assert costs["total_cost"] == pytest.approx(18.00)

def test_calculate_cost_gemini_is_free():
    costs = _calculate_cost("gemini-2.0-flash", 1_000_000, 1_000_000)
    assert costs["total_cost"] == 0.0

def test_calculate_cost_zero_tokens():
    costs = _calculate_cost("claude-haiku-4-5-20251001", 0, 0)
    assert costs["total_cost"] == 0.0

def test_calculate_cost_partial_tokens():
    costs = _calculate_cost("claude-haiku-4-5-20251001", 100, 50)
    assert costs["input_cost"]  == pytest.approx((100 / 1_000_000) * 0.80)
    assert costs["output_cost"] == pytest.approx((50  / 1_000_000) * 4.00)

def test_all_models_have_pricing():
    for provider, model in MODELS.values():
        assert model in PRICING, f"{model} missing from PRICING"

def test_models_map_keys():
    assert set(MODELS.keys()) == {"low", "medium", "high"}

def test_low_medium_routes_to_gemini():
    assert MODELS["low"][0]    == "gemini"
    assert MODELS["medium"][0] == "gemini"

def test_high_routes_to_claude():
    assert MODELS["high"][0] == "claude"

def test_routed_call_low_uses_gemini(tmp_db, tmp_cache, mock_gemini, mocker):
    mocker.patch("api_cost_tracker.tracker.save_record")
    from api_cost_tracker.router import routed_call

    record = routed_call("What is 5 + 3?")

    assert record.provider         == "gemini"
    assert record.model_used       == "gemini-2.0-flash"
    assert record.total_cost       == 0.0
    assert record.cache_hit        is False
    assert record.response_preview == "8"

def test_routed_call_cache_hit(tmp_db, tmp_cache, mock_gemini, mocker):
    mocker.patch("api_cost_tracker.tracker.save_record")
    from api_cost_tracker.router import routed_call

    routed_call("What is 5 + 3?")
    mock_gemini.generate_content.reset_mock()

    record = routed_call("What is 5 + 3?")
    assert record.cache_hit is True
    mock_gemini.generate_content.assert_not_called()

def test_routed_call_unknown_complexity_fallback(tmp_db, tmp_cache, mock_gemini, mock_anthropic, mocker):
    """Falls back to claude-sonnet if classifier returns unexpected value."""
    mock_gemini.generate_content.side_effect = [
        type("R", (), {"text": "banana"})(),  # classifier returns garbage
        type("R", (), {"text": "answer", "usage_metadata": type("U", (), {"prompt_token_count": 10, "candidates_token_count": 5})()})(),
    ]
    mocker.patch("api_cost_tracker.tracker.save_record")
    from api_cost_tracker.router import routed_call

    record = routed_call("some prompt")
    # fallback provider is claude, model is claude-sonnet-4-6
    assert record.provider   == "claude"
    assert record.model_used == "claude-sonnet-4-6"
