from decimal import Decimal as D

from conftest import build
from personal_portfolio_manager.data import AssetClass
from personal_portfolio_manager.portfolio import value_plan, weights
from personal_portfolio_manager.risk import deviation_alerts, find_breaches


def _breaches(plan):
    v = value_plan(plan)
    return find_breaches(plan, v.instrument_values(), v.class_values(), v.total)


def test_stock_exactly_at_cap_is_not_a_breach():
    # stock 500 of 10000 total = 5%
    plan = build(holdings=[{"instrument_id": "STOCK_A", "quantity": "5"}], cash=[{"amount": "9500"}])
    assert _breaches(plan) == []


def test_stock_above_cap_is_a_breach():
    plan = build(holdings=[{"instrument_id": "STOCK_A", "quantity": "6"}], cash=[{"amount": "9400"}])
    [b] = _breaches(plan)
    assert (b.subject, b.scope, b.limit) == ("STOCK_A", "instrument", D("0.05"))
    assert b.weight == D("0.06")


def test_fund_cap_and_silver_class_cap():
    plan = build(
        holdings=[
            {"instrument_id": "EQ_FUND", "quantity": "800"},  # 1600 = 16%
            {"instrument_id": "SILVER", "quantity": "20"},  # 800 = 8%
        ],
        cash=[{"amount": "7600"}],
    )
    assert {(b.subject, b.scope) for b in _breaches(plan)} == {
        ("EQ_FUND", "instrument"),
        ("silver", "asset_class"),
    }


def test_commodity_and_currency_have_no_instrument_cap():
    plan = build(holdings=[{"instrument_id": "GOLD", "quantity": "1"}])
    assert _breaches(plan) == []


def test_deviation_alert_at_exactly_band():
    # gold 25% vs 20% target -> exactly 5pp -> alert
    plan = build(holdings=[{"instrument_id": "GOLD", "quantity": "1"}], cash=[{"amount": "9000"}])
    v = value_plan(plan)
    alerts = deviation_alerts(plan, weights(v.class_values(), v.total), v.total)
    gold = [a for a in alerts if a.asset_class is AssetClass.GOLD]
    assert gold and gold[0].deviation == D("0.05")


def test_no_alerts_or_breaches_for_empty_portfolio(plan):
    v = value_plan(plan)
    assert deviation_alerts(plan, weights(v.class_values(), v.total), v.total) == []
    assert _breaches(plan) == []
