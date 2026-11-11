"""Concentration caps and target-deviation review alerts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from ..data.models import AssetClass, Instrument, InstrumentKind, Limits, Plan


@dataclass(frozen=True)
class Breach:
    subject: str
    weight: Decimal
    limit: Decimal
    scope: str  # "instrument" or "asset_class"


@dataclass(frozen=True)
class DeviationAlert:
    asset_class: AssetClass
    weight: Decimal
    target: Decimal

    @property
    def deviation(self) -> Decimal:
        return self.weight - self.target


def instrument_cap(limits: Limits, instrument: Instrument) -> Decimal | None:
    if instrument.kind is InstrumentKind.STOCK:
        return limits.max_single_stock
    if instrument.kind is InstrumentKind.FUND:
        return limits.max_single_fund
    return None


def class_cap(limits: Limits, asset_class: AssetClass) -> Decimal | None:
    return limits.max_asset_class.get(asset_class)


def find_breaches(
    plan: Plan,
    instrument_values: Mapping[str, Decimal],
    class_values: Mapping[AssetClass, Decimal],
    total: Decimal,
) -> list[Breach]:
    """Weights strictly above a cap. Sitting exactly on a cap is allowed."""
    if total == 0:
        return []
    breaches: list[Breach] = []
    for inst_id, value in sorted(instrument_values.items()):
        cap = instrument_cap(plan.limits, plan.instrument(inst_id))
        if cap is not None and value / total > cap:
            breaches.append(Breach(inst_id, value / total, cap, "instrument"))
    for ac, value in class_values.items():
        cap = class_cap(plan.limits, ac)
        if cap is not None and value / total > cap:
            breaches.append(Breach(ac.value, value / total, cap, "asset_class"))
    return breaches


def deviation_alerts(
    plan: Plan, class_weights: Mapping[AssetClass, Decimal], total: Decimal
) -> list[DeviationAlert]:
    """Classes whose weight is at least ``deviation_band`` away from target."""
    if total == 0:
        return []
    band = plan.limits.deviation_band
    alerts = []
    for ac, w in class_weights.items():
        target = plan.target_weight(ac)
        if abs(w - target) >= band:
            alerts.append(DeviationAlert(ac, w, target))
    return alerts
