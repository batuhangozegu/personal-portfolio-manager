"""TRY valuation of the portfolio bucket, plus the separate emergency balance."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import TypeVar

from ..data.models import BASE_CURRENCY, AssetClass, Bucket, CashBalance, Instrument, Plan

K = TypeVar("K")
ZERO = Decimal(0)


@dataclass(frozen=True)
class Position:
    instrument: Instrument
    quantity: Decimal
    value: Decimal


@dataclass(frozen=True)
class Valuation:
    """Portfolio-bucket state. Emergency holdings only appear as one balance."""

    positions: tuple[Position, ...]
    cash_available: Decimal
    cash_pending: tuple[CashBalance, ...]
    emergency_balance: Decimal

    @property
    def cash_pending_total(self) -> Decimal:
        return sum((c.amount for c in self.cash_pending), ZERO)

    @property
    def total(self) -> Decimal:
        invested = sum((p.value for p in self.positions), ZERO)
        return invested + self.cash_available + self.cash_pending_total

    def class_values(self) -> dict[AssetClass, Decimal]:
        values = {ac: ZERO for ac in AssetClass}
        for p in self.positions:
            values[p.instrument.asset_class] += p.value
        # TRY cash, including cash awaiting settlement, is TRY-liquid exposure.
        values[AssetClass.TRY_LIQUID] += self.cash_available + self.cash_pending_total
        return values

    def instrument_values(self) -> dict[str, Decimal]:
        return {p.instrument.id: p.value for p in self.positions}


def weights(values: Mapping[K, Decimal], total: Decimal) -> dict[K, Decimal]:
    """Value shares of ``total``; all zero for an empty portfolio."""
    if total == 0:
        return {k: ZERO for k in values}
    return {k: v / total for k, v in values.items()}


def is_settled(cash: CashBalance, plan: Plan) -> bool:
    return cash.available_on is None or cash.available_on <= plan.as_of


def value_plan(plan: Plan) -> Valuation:
    positions: list[Position] = []
    emergency = ZERO
    for h in plan.holdings:
        inst = plan.instrument(h.instrument_id)
        value = h.quantity * plan.price_try(inst)
        if h.bucket is Bucket.PORTFOLIO:
            positions.append(Position(inst, h.quantity, value))
        else:
            emergency += value

    available = ZERO
    pending: list[CashBalance] = []
    for c in plan.cash:
        if c.bucket is Bucket.EMERGENCY:
            emergency += c.amount
        elif is_settled(c, plan):
            available += c.amount
        else:
            pending.append(c)

    pending.sort(key=lambda c: c.available_on)
    return Valuation(tuple(positions), available, tuple(pending), emergency)


def stale_inputs(plan: Plan) -> list[str]:
    """Prices or FX rates needed for this run that are older than allowed."""
    cutoff = plan.as_of - timedelta(days=plan.limits.max_price_age_days)
    needed = {h.instrument_id for h in plan.holdings}
    needed |= {i for t in plan.targets for i in t.buy_instruments}

    problems: list[str] = []
    currencies: set[str] = set()
    for inst_id in sorted(needed):
        inst = plan.instrument(inst_id)
        currencies.add(inst.currency)
        if inst.price_as_of < cutoff:
            problems.append(f"{inst.id} fiyatı eski ({inst.price_as_of})")
    for rate in plan.fx_rates:
        if rate.currency in currencies and rate.currency != BASE_CURRENCY and rate.as_of < cutoff:
            problems.append(f"{rate.currency} kuru eski ({rate.as_of})")
    return problems
