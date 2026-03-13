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

def test_calculate_cost_zero_tokens():
    costs = _calculate_cost("claude-haiku-4-5-20251001", 0, 0)
    assert costs["total_cost"] == 0.0

def test_calculate_cost_partial_tokens():
    costs = _calculate_cost("claude-haiku-4-5-20251001", 100, 50)
    assert costs["input_cost"]  == pytest.approx((100 / 1_000_000) * 0.80)
    assert costs["output_cost"] == pytest.approx((50  / 1_000_000) * 4.00)

def test_all_models_have_pricing():
    for model in MODELS.values():
        assert model in PRICING, f"{model} missing from PRICING"

def test_models_map_keys():
    assert set(MODELS.keys()) == {"low", "medium", "high"}

def test_routed_call(tmp_db, tmp_cache, mock_anthropic, mocker):
    mocker.patch("api_cost_tracker.tracker.save_record")
    from api_cost_tracker.router import routed_call

    record = routed_call("What is 5 + 3?")

    assert record.complexity       == "low"
    assert record.model_used       == "claude-haiku-4-5-20251001"
    assert record.input_tokens     == 32
    assert record.output_tokens    == 5
    assert record.cache_hit        is False
    assert record.response_preview == "8"
    assert record.total_cost       > 0

def test_routed_call_cache_hit(tmp_db, tmp_cache, mock_anthropic, mocker):
    mocker.patch("api_cost_tracker.tracker.save_record")
    from api_cost_tracker.router import routed_call

    routed_call("What is 5 + 3?")
    mock_anthropic.messages.create.reset_mock()

    record = routed_call("What is 5 + 3?")
    assert record.cache_hit is True
    mock_anthropic.messages.create.assert_not_called()

def test_routed_call_unknown_complexity(tmp_db, tmp_cache, mock_anthropic, mocker):
    mock_anthropic.messages.create.side_effect[0].content[0].text = "banana"
    mocker.patch("api_cost_tracker.tracker.save_record")
    from api_cost_tracker.router import routed_call

    record = routed_call("some prompt")
    assert record.model_used == "claude-sonnet-4-6"
