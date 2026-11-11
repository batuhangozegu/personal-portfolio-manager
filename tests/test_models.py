import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from conftest import BASE, build, raw
from personal_portfolio_manager.data import Plan, parse_plan


def test_base_plan_is_valid(plan):
    assert plan.limits.max_single_stock == Decimal("0.05")
    assert plan.price_try(plan.instrument("USD")) == Decimal(40)


def test_json_numbers_keep_decimal_precision():
    data = raw()
    data["targets"] = [
        {"asset_class": "equity", "weight": 0.1},
        {"asset_class": "gold", "weight": 0.2},
        {"asset_class": "try_liquid", "weight": 0.7},
    ]
    # 0.1 + 0.2 + 0.7 != 1 in binary floats; must still validate.
    plan = parse_plan(json.dumps(data))
    assert plan.targets[0].weight == Decimal("0.1")


def test_weights_must_sum_to_one():
    data = raw()
    data["targets"][0]["weight"] = "0.39"
    with pytest.raises(ValidationError, match="sum to exactly 1"):
        Plan.model_validate(data)


def test_holding_must_reference_known_instrument():
    with pytest.raises(ValidationError, match="unknown instrument"):
        build(holdings=[{"instrument_id": "NOPE", "quantity": "1"}])


def test_duplicate_holding_in_same_bucket_rejected():
    h = {"instrument_id": "GOLD", "quantity": "1"}
    with pytest.raises(ValidationError, match="duplicate holding"):
        build(holdings=[h, h])


def test_same_instrument_allowed_in_both_buckets():
    plan = build(holdings=[
        {"instrument_id": "MMF", "quantity": "10", "bucket": "portfolio"},
        {"instrument_id": "MMF", "quantity": "10", "bucket": "emergency"},
    ])
    assert len(plan.holdings) == 2


def test_missing_fx_rate_rejected():
    with pytest.raises(ValidationError, match="missing fx rates"):
        build(fx_rates=[])


def test_future_dated_price_rejected():
    data = raw()
    data["instruments"][2]["price_as_of"] = "2026-11-12"
    with pytest.raises(ValidationError, match="after plan date"):
        Plan.model_validate(data)


def test_buy_instrument_must_match_asset_class():
    data = raw()
    data["targets"][1]["buy_instrument"] = "USD"
    with pytest.raises(ValidationError, match="is fx"):
        Plan.model_validate(data)


def test_negative_contribution_rejected():
    with pytest.raises(ValidationError):
        build(contribution="-1")


def test_unknown_fields_rejected():
    with pytest.raises(ValidationError):
        build(surprise=True)


def test_emergency_target_is_monthly_expense_times_months():
    plan = build(emergency_fund={"monthly_expense": "8000"})
    assert plan.emergency_fund.months == 6
    assert plan.emergency_fund.target == Decimal(48000)


def test_base_fixture_not_mutated():
    build(contribution="1")
    assert BASE["contribution"] == "10000"
