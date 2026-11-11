from decimal import Decimal as D

from conftest import build, raw
from personal_portfolio_manager.data import AssetClass, Plan
from personal_portfolio_manager.portfolio import stale_inputs, value_plan, weights


def test_empty_portfolio_has_zero_total_and_zero_weights(plan):
    v = value_plan(plan)
    assert v.total == 0
    assert all(w == 0 for w in weights(v.class_values(), v.total).values())


def test_values_use_fx_rates():
    v = value_plan(build(holdings=[{"instrument_id": "USD", "quantity": "100"}]))
    assert v.class_values()[AssetClass.FX] == D(4000)


def test_emergency_bucket_excluded_from_portfolio():
    plan = build(
        holdings=[
            {"instrument_id": "MMF", "quantity": "5000", "bucket": "emergency"},
            {"instrument_id": "GOLD", "quantity": "1"},
        ],
        cash=[{"amount": "700", "bucket": "emergency"}],
    )
    v = value_plan(plan)
    assert v.emergency_balance == D(5700)
    assert v.total == D(3000)
    assert v.class_values()[AssetClass.TRY_LIQUID] == 0


def test_pending_cash_counts_in_value_but_not_available():
    plan = build(cash=[
        {"amount": "1000"},
        {"amount": "2000", "available_on": "2026-11-11"},
        {"amount": "500", "available_on": "2026-11-13", "note": "sale T+2"},
    ])
    v = value_plan(plan)
    assert v.cash_available == D(3000)
    assert v.cash_pending_total == D(500)
    assert v.total == D(3500)
    assert v.class_values()[AssetClass.TRY_LIQUID] == D(3500)


def test_weights_sum_to_one():
    plan = build(holdings=[
        {"instrument_id": "GOLD", "quantity": "1"},
        {"instrument_id": "USD", "quantity": "25"},
    ])
    v = value_plan(plan)
    w = weights(v.class_values(), v.total)
    assert w[AssetClass.GOLD] == D("0.75")
    assert sum(w.values()) == 1


def test_stale_price_detected_for_held_instrument():
    data = raw(holdings=[{"instrument_id": "STOCK_A", "quantity": "1"}])
    data["instruments"][0]["price_as_of"] = "2026-11-07"
    assert stale_inputs(Plan.model_validate(data)) == ["STOCK_A fiyatı eski (2026-11-07)"]


def test_price_exactly_at_age_limit_is_fresh():
    data = raw(holdings=[{"instrument_id": "STOCK_A", "quantity": "1"}])
    data["instruments"][0]["price_as_of"] = "2026-11-08"  # 3 days, limit is 3
    assert stale_inputs(Plan.model_validate(data)) == []


def test_unused_stale_instrument_ignored():
    data = raw()
    data["instruments"][0]["price_as_of"] = "2020-01-01"  # STOCK_A neither held nor bought
    assert stale_inputs(Plan.model_validate(data)) == []


def test_stale_fx_rate_detected():
    data = raw()
    data["fx_rates"][0]["as_of"] = "2026-11-01"
    assert stale_inputs(Plan.model_validate(data)) == ["USD kuru eski (2026-11-01)"]
