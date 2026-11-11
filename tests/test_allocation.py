from decimal import Decimal as D

import pytest

from conftest import build, raw
from personal_portfolio_manager.data import AssetClass, Plan
from personal_portfolio_manager.strategies import (
    AWAITING_REVIEW,
    BLOCKED,
    allocate,
    proportional_fill,
    split_contribution,
)
from personal_portfolio_manager.data import EmergencyFund


def _bought(p):
    return {x.instrument_id: x.quantity for x in p.purchases}


# --- emergency split -------------------------------------------------------

def test_no_emergency_config_sends_everything_to_portfolio():
    s = split_contribution(D(1000), None, D(0))
    assert (s.to_emergency, s.to_portfolio, s.configured) == (0, D(1000), False)


def test_contribution_below_shortfall_goes_fully_to_emergency():
    s = split_contribution(D(1000), EmergencyFund(monthly_expense=D(500)), D(0))
    assert (s.target, s.to_emergency, s.to_portfolio) == (D(3000), D(1000), 0)


def test_contribution_above_shortfall_is_split():
    s = split_contribution(D(1000), EmergencyFund(monthly_expense=D(500)), D(2600))
    assert (s.to_emergency, s.to_portfolio, s.shortfall_after) == (D(400), D(600), 0)


def test_full_or_overfull_emergency_fund_takes_nothing():
    s = split_contribution(D(1000), EmergencyFund(monthly_expense=D(500)), D(9000))
    assert (s.to_emergency, s.to_portfolio) == (0, D(1000))


# --- proportional fill ----------------------------------------------------

def test_proportional_fill_redistributes_capped_share():
    eq, gold, fx = AssetClass.EQUITY, AssetClass.GOLD, AssetClass.FX
    out = proportional_fill(D(900), {eq: D(400), gold: D(400), fx: D(400)}, {eq: D(100), gold: D(400), fx: D(400)})
    assert out == {eq: D(100), gold: D(400), fx: D(400)}


def test_proportional_fill_leaves_money_when_all_capped():
    eq = AssetClass.EQUITY
    assert proportional_fill(D(500), {eq: D(400)}, {eq: D(200)}) == {eq: D(200)}


# --- allocation -----------------------------------------------------------

def test_empty_portfolio_lands_on_targets(plan):
    p = allocate(plan)
    assert p.status == AWAITING_REVIEW
    assert _bought(p) == {
        "EQ_FUND": D(667),      # equity 4000 TRY split over three funds,
        "EQ_FUND_B": D(667),    # each within the 15% single-fund cap
        "EQ_FUND_C": D(666),
        "GOLD": D("0.66"),      # 1980 TRY; one more 0.01 g (30 TRY) does not fit
        "USD": D("50.00"),      # 2000 TRY
        "MMF": D(1500),
        "SILVER": D("12.50"),   # 500 TRY
    }
    assert p.remaining_cash == D(20)
    assert p.conserves_cash()
    assert p.weights_after[AssetClass.EQUITY] == D("0.4")


def test_emergency_fund_filled_before_portfolio():
    p = allocate(build(emergency_fund={"monthly_expense": "5000"}))
    assert p.to_emergency == D(10000)
    assert p.purchases == ()
    assert p.conserves_cash()
    assert "acil durum fonu" in p.notes[0]


def test_remainder_after_emergency_shortfall_is_invested():
    p = allocate(build(
        emergency_fund={"monthly_expense": "5000"},
        cash=[{"amount": "25000", "bucket": "emergency"}],
    ))
    assert p.to_emergency == D(5000)
    assert p.budget == D(5000)
    assert p.purchased_total + p.remaining_cash + p.kept_cash == D(5000)


def test_zero_contribution_on_empty_portfolio():
    p = allocate(build(contribution="0"))
    assert p.purchases == () and p.remaining_cash == 0 and p.total_after == 0
    assert p.conserves_cash()


def test_pending_settlement_cash_is_not_spent():
    p = allocate(build(contribution="0", cash=[{"amount": "5000", "available_on": "2026-11-13"}]))
    assert p.budget == 0 and p.purchases == ()
    assert any("takasta" in n and "2026-11-13" in n for n in p.notes)


def test_settled_cash_is_deployed():
    p = allocate(build(contribution="0", cash=[{"amount": "5000", "available_on": "2026-11-10"}]))
    assert p.budget == D(5000)
    assert p.purchased_total > D(4900)
    assert p.conserves_cash()


def test_stock_cap_limits_purchase_and_leaves_rest_as_cash():
    data = raw()
    data["targets"][0]["buy_instruments"] = ["STOCK_A"]
    p = allocate(Plan.model_validate(data))
    assert _bought(p)["STOCK_A"] == D(5)  # 5% of 10000
    assert p.breaches_after == ()
    assert p.remaining_cash == D(3520)  # 3500 equity excess + 20 gold rounding
    assert any("limitler nedeniyle" in n for n in p.notes)
    assert p.conserves_cash()


def test_single_fund_cap_spreads_class_across_instruments():
    data = raw()
    data["targets"][0]["buy_instruments"] = ["EQ_FUND"]
    p = allocate(Plan.model_validate(data))
    assert _bought(p)["EQ_FUND"] == D(750)  # 1500 TRY = 15% cap, not the 4000 target
    data["targets"][0]["buy_instruments"] = ["EQ_FUND", "EQ_FUND_B", "EQ_FUND_C"]
    p = allocate(Plan.model_validate(data))
    assert p.weights_after[AssetClass.EQUITY] == D("0.4")


def test_instrument_near_cap_overflows_to_class_siblings():
    plan = build(holdings=[{"instrument_id": "EQ_FUND", "quantity": "700"}])  # 1400 TRY
    p = allocate(plan)
    bought = _bought(p)
    assert bought.get("EQ_FUND", 0) < bought["EQ_FUND_B"]
    assert p.breaches_after == ()
    assert p.conserves_cash()


def test_silver_class_cap_respected():
    plan = build(
        holdings=[{"instrument_id": "SILVER", "quantity": "180"}],  # 7200 TRY
        cash=[{"amount": "92800", "bucket": "portfolio"}],
        contribution="0",
    )
    # total 100000; silver already 7.2%, target 5% -> no silver purchase
    p = allocate(plan)
    assert "SILVER" not in _bought(p)
    assert p.weights_after[AssetClass.SILVER] <= D("0.075")


def test_overweight_class_gets_nothing_and_no_sales():
    plan = build(holdings=[{"instrument_id": "GOLD", "quantity": "5"}])  # 15000 gold
    p = allocate(plan)
    assert "GOLD" not in _bought(p)
    assert all(x.quantity > 0 and x.cost > 0 for x in p.purchases)
    assert p.conserves_cash()


def test_existing_breach_is_reported():
    plan = build(holdings=[{"instrument_id": "STOCK_A", "quantity": "10"}], contribution="0",
                 cash=[{"amount": "9000"}])
    p = allocate(plan)
    assert [b.subject for b in p.breaches_before] == ["STOCK_A"]


def test_class_without_buy_instrument_stays_cash():
    data = raw()
    data["targets"][1]["buy_instruments"] = []
    p = allocate(Plan.model_validate(data))
    assert "GOLD" not in _bought(p)
    assert p.remaining_cash == D(2000)
    assert any("Altın için alım enstrümanı tanımlı değil" in n for n in p.notes)


def test_try_liquid_without_instrument_is_kept_cash():
    data = raw()
    data["targets"][3]["buy_instruments"] = []
    p = allocate(Plan.model_validate(data))
    assert p.kept_cash == D(1500)
    assert p.conserves_cash()


def test_stale_price_blocks_proposal():
    data = raw()
    data["instruments"][4]["price_as_of"] = "2026-11-01"
    p = allocate(Plan.model_validate(data))
    assert p.status == BLOCKED
    assert p.purchases == ()
    assert p.remaining_cash == D(10000)
    assert p.blockers == ("GOLD fiyatı eski (2026-11-01)",)
    assert p.conserves_cash()


@pytest.mark.parametrize("contribution", ["0", "1", "0.37", "99.99", "1234.56", "37000", "1000000"])
@pytest.mark.parametrize("emergency", [None, {"monthly_expense": "1000"}])
def test_cash_conservation_and_caps(contribution, emergency):
    plan = build(
        contribution=contribution,
        emergency_fund=emergency,
        holdings=[
            {"instrument_id": "STOCK_A", "quantity": "7"},
            {"instrument_id": "GOLD", "quantity": "0.5"},
            {"instrument_id": "MMF", "quantity": "2500", "bucket": "emergency"},
        ],
        cash=[{"amount": "812.45"}, {"amount": "300", "available_on": "2026-11-13"}],
    )
    p = allocate(plan)
    assert p.conserves_cash()
    assert p.remaining_cash >= 0 and p.kept_cash >= 0
    new_breaches = {b.subject for b in p.breaches_after} - {b.subject for b in p.breaches_before}
    assert not new_breaches
    assert sum(p.weights_after.values()) in (0, 1) or abs(sum(p.weights_after.values()) - 1) < D("1e-20")
