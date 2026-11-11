"""Synthetic plan builders. Prices and instruments are invented, not market data."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from personal_portfolio_manager.data import Plan

BASE: dict[str, Any] = {
    "as_of": "2026-11-11",
    "contribution": "10000",
    "fx_rates": [{"currency": "USD", "rate_to_try": "40", "as_of": "2026-11-11", "source": "synthetic"}],
    "instruments": [
        {"id": "STOCK_A", "name": "Synthetic stock A", "kind": "stock", "asset_class": "equity",
         "price": "100", "price_as_of": "2026-11-11", "min_increment": "1", "settlement_days": 2},
        {"id": "EQ_FUND", "name": "Synthetic equity fund", "kind": "fund", "asset_class": "equity",
         "price": "2", "price_as_of": "2026-11-11", "min_increment": "1", "settlement_days": 2},
        {"id": "GOLD", "name": "Synthetic gram gold", "kind": "commodity", "asset_class": "gold",
         "price": "3000", "price_as_of": "2026-11-11", "min_increment": "0.01", "settlement_days": 0},
        {"id": "SILVER", "name": "Synthetic gram silver", "kind": "commodity", "asset_class": "silver",
         "price": "40", "price_as_of": "2026-11-11", "min_increment": "0.01", "settlement_days": 0},
        {"id": "USD", "name": "US dollar", "kind": "currency", "asset_class": "fx", "currency": "USD",
         "price": "1", "price_as_of": "2026-11-11", "min_increment": "0.01", "settlement_days": 0},
        {"id": "MMF", "name": "Synthetic money-market fund", "kind": "fund", "asset_class": "try_liquid",
         "price": "1", "price_as_of": "2026-11-11", "min_increment": "1", "settlement_days": 1},
    ],
    "holdings": [],
    "cash": [],
    "targets": [
        {"asset_class": "equity", "weight": "0.40", "buy_instrument": "EQ_FUND"},
        {"asset_class": "gold", "weight": "0.20", "buy_instrument": "GOLD"},
        {"asset_class": "fx", "weight": "0.20", "buy_instrument": "USD"},
        {"asset_class": "try_liquid", "weight": "0.15", "buy_instrument": "MMF"},
        {"asset_class": "silver", "weight": "0.05", "buy_instrument": "SILVER"},
    ],
}


def build(**overrides: Any) -> Plan:
    data = copy.deepcopy(BASE)
    data.update(overrides)
    return Plan.model_validate(data)


def raw(**overrides: Any) -> dict[str, Any]:
    data = copy.deepcopy(BASE)
    data.update(overrides)
    return data


@pytest.fixture
def plan() -> Plan:
    return build()
