"""Contribution-only allocation: buy toward target deficits, never sell.

Steps (see docs/decisions.md):

1. Block the run if a required price or FX rate is stale.
2. Fill the emergency fund shortfall first; the rest is portfolio money.
3. Budget = portfolio share of the contribution + settled portfolio TRY cash.
   Cash awaiting settlement is never spent.
4. Split the budget across under-target asset classes in proportion to their
   deficits, each limited by its deficit, its class cap and the combined room
   of its buy instruments. Money a capped class cannot take flows to the
   other classes, up to their limits.
5. Inside a class, split evenly across its buy instruments, each within its
   own cap (e.g. 15% per fund), with overflow going to the class's others.
6. Round down to each instrument's ``min_increment``; spend the leftover one
   unit at a time on the class furthest below target that can still take it.
7. Whatever is left stays as TRY cash and is reported with a reason.

Invariant: to_emergency + purchases + kept_cash + remaining_cash
           == contribution + settled portfolio cash.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_FLOOR, Decimal
from typing import TypeVar

from ..data.models import AssetClass, CashBalance, Instrument, Plan
from ..labels import CLASS_LABELS, pct, tl
from ..portfolio.valuation import stale_inputs, value_plan, weights
from ..risk.limits import Breach, DeviationAlert, class_cap, deviation_alerts, find_breaches, instrument_cap
from .emergency import EmergencySplit, split_contribution

ZERO = Decimal(0)
K = TypeVar("K")
CENT = Decimal("0.01")

AWAITING_REVIEW = "awaiting_review"
BLOCKED = "blocked"


@dataclass(frozen=True)
class Purchase:
    instrument_id: str
    instrument_name: str
    asset_class: AssetClass
    quantity: Decimal
    unit_price: Decimal
    cost: Decimal
    reason: str


@dataclass(frozen=True)
class Proposal:
    status: str
    as_of: date
    contribution: Decimal
    cash_available_before: Decimal
    emergency: EmergencySplit | None
    budget: Decimal
    purchases: tuple[Purchase, ...]
    kept_cash: Decimal
    remaining_cash: Decimal
    pending_cash: tuple[CashBalance, ...]
    total_before: Decimal
    total_after: Decimal
    weights_before: Mapping[AssetClass, Decimal]
    weights_after: Mapping[AssetClass, Decimal]
    targets: Mapping[AssetClass, Decimal]
    breaches_before: tuple[Breach, ...]
    breaches_after: tuple[Breach, ...]
    alerts_after: tuple[DeviationAlert, ...]
    notes: tuple[str, ...]
    blockers: tuple[str, ...]

    @property
    def purchased_total(self) -> Decimal:
        return sum((p.cost for p in self.purchases), ZERO)

    @property
    def to_emergency(self) -> Decimal:
        return self.emergency.to_emergency if self.emergency else ZERO

    def conserves_cash(self) -> bool:
        out = self.to_emergency + self.purchased_total + self.kept_cash + self.remaining_cash
        return out == self.contribution + self.cash_available_before


def _floor(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(rounding=ROUND_FLOOR) * step


def proportional_fill(
    budget: Decimal, shares: Mapping[K, Decimal], caps: Mapping[K, Decimal]
) -> dict[K, Decimal]:
    """Split ``budget`` in proportion to ``shares``, never exceeding ``caps``.

    A key that would exceed its cap is pinned at the cap and the rest is
    re-split among the others. Results are floored to whole kuruş and keep
    the key order of ``shares``, so the outcome is deterministic.
    """
    fixed: dict[K, Decimal] = {}
    free = [c for c, s in shares.items() if s > 0]  # list, not set: keep input order
    while free:
        rest = budget - sum(fixed.values(), ZERO)
        total_share = sum((shares[c] for c in free), ZERO)
        tentative = {c: rest * shares[c] / total_share for c in free}
        over = [c for c in free if tentative[c] > caps[c]]
        if not over:
            fixed.update(tentative)
            break
        for c in over:
            fixed[c] = caps[c]
        free = [c for c in free if c not in over]
    return {c: _floor(fixed[c], CENT) for c in shares if c in fixed}


def allocate(plan: Plan) -> Proposal:
    val = value_plan(plan)
    targets = {ac: plan.target_weight(ac) for ac in AssetClass}
    total_before = val.total
    class_before = val.class_values()
    weights_before = weights(class_before, total_before)
    breaches_before = tuple(find_breaches(plan, val.instrument_values(), class_before, total_before))
    pending_notes = tuple(
        f"{tl(c.amount)} takasta, {c.available_on} tarihinde kullanılabilir olacak; bu öneride harcanmadı."
        + (f" ({c.note})" if c.note else "")
        for c in val.cash_pending
    )

    blockers = tuple(stale_inputs(plan))
    if blockers:
        budget = plan.contribution + val.cash_available
        return Proposal(
            status=BLOCKED, as_of=plan.as_of, contribution=plan.contribution,
            cash_available_before=val.cash_available, emergency=None, budget=budget,
            purchases=(), kept_cash=ZERO, remaining_cash=budget, pending_cash=val.cash_pending,
            total_before=total_before, total_after=total_before,
            weights_before=weights_before, weights_after=weights_before, targets=targets,
            breaches_before=breaches_before, breaches_after=breaches_before, alerts_after=(),
            notes=("Güncel olmayan veri var; fiyatları güncelleyip tekrar çalıştır.", *pending_notes),
            blockers=blockers,
        )

    split = split_contribution(plan.contribution, plan.emergency_fund, val.emergency_balance)
    budget = split.to_portfolio + val.cash_available
    total = total_before + split.to_portfolio  # value after the run; purchases only move money

    # Settled cash is what we allocate, so it is not counted as already held.
    base = dict(class_before)
    base[AssetClass.TRY_LIQUID] -= val.cash_available
    inst_before = val.instrument_values()

    notes: list[str] = []
    deficit = {ac: max(ZERO, targets[ac] * total - base[ac]) for ac in AssetClass}
    class_room: dict[AssetClass, Decimal] = {}
    inst_room: dict[str, Decimal] = {}
    members: dict[AssetClass, list[Instrument]] = {}
    for t in plan.targets:
        ac = t.asset_class
        if deficit[ac] == 0:
            continue
        insts = [plan.instrument(i) for i in t.buy_instruments]
        if not insts and ac is not AssetClass.TRY_LIQUID:
            notes.append(f"{CLASS_LABELS[ac]} için alım enstrümanı tanımlı değil; payı nakitte kalır.")
            continue
        limit = deficit[ac]
        cap = class_cap(plan.limits, ac)
        if cap is not None:
            limit = min(limit, max(ZERO, cap * total - base[ac]))
        if insts:
            capacity = ZERO
            for inst in insts:
                icap = instrument_cap(plan.limits, inst)
                r = limit if icap is None else max(ZERO, icap * total - inst_before.get(inst.id, ZERO))
                inst_room[inst.id] = min(r, limit)
                capacity += inst_room[inst.id]
            limit = min(limit, capacity)
        if limit < deficit[ac]:
            notes.append(
                f"{CLASS_LABELS[ac]}: limitler nedeniyle en fazla {tl(limit)} alınabilir "
                f"(hedefe ulaşmak için {tl(deficit[ac])} gerekirdi)."
            )
        if limit > 0:
            class_room[ac] = limit
            members[ac] = insts

    class_amounts = proportional_fill(budget, {ac: deficit[ac] for ac in class_room}, class_room)

    # Within a class, split evenly across its buy instruments, each within its own cap.
    kept_cash = ZERO
    units: dict[str, Decimal] = {}
    unit_cost: dict[str, Decimal] = {}
    owner: dict[str, AssetClass] = {}
    for ac, amount in class_amounts.items():
        insts = members[ac]
        if not insts:
            kept_cash += amount
            continue
        shares = proportional_fill(
            amount, {i.id: Decimal(1) for i in insts}, {i.id: inst_room[i.id] for i in insts}
        )
        for inst in insts:
            uc = plan.price_try(inst) * inst.min_increment
            unit_cost[inst.id], owner[inst.id] = uc, ac
            units[inst.id] = (shares.get(inst.id, ZERO) / uc).to_integral_value(rounding=ROUND_FLOOR)

    def spent_in(ac: AssetClass) -> Decimal:
        return sum((units[i] * unit_cost[i] for i in units if owner[i] is ac), ZERO)

    leftover = budget - kept_cash - sum((units[i] * unit_cost[i] for i in units), ZERO)
    while True:
        best, best_key = None, None
        for inst_id, uc in unit_cost.items():
            ac = owner[inst_id]
            spent_inst, spent_class = units[inst_id] * uc, spent_in(ac)
            if uc > leftover or spent_class + uc > class_room[ac] or spent_inst + uc > inst_room[inst_id]:
                continue
            key = (deficit[ac] - spent_class, -spent_inst)
            if best_key is None or key > best_key:
                best, best_key = inst_id, key
        if best is None:
            break
        units[best] += 1
        leftover -= unit_cost[best]
    if leftover < 0:  # pragma: no cover - guarded by construction
        raise AssertionError("allocation overspent the budget")

    class_after = dict(base)
    class_after[AssetClass.TRY_LIQUID] += kept_cash + leftover
    inst_after = dict(inst_before)
    bought: list[tuple[AssetClass, Instrument, Decimal, Decimal]] = []
    for inst_id, n in units.items():
        if n == 0:
            continue
        inst, ac, cost = plan.instrument(inst_id), owner[inst_id], n * unit_cost[inst_id]
        class_after[ac] += cost
        inst_after[inst_id] = inst_after.get(inst_id, ZERO) + cost
        bought.append((ac, inst, n * inst.min_increment, cost))
    weights_after = weights(class_after, total)

    purchases = tuple(
        Purchase(
            instrument_id=inst.id, instrument_name=inst.name, asset_class=ac,
            quantity=quantity, unit_price=plan.price_try(inst), cost=cost,
            reason=(
                f"{CLASS_LABELS[ac]}, katkı sonrası portföyde hedefe {tl(deficit[ac])} eksik kalıyordu. "
                f"Hedef {pct(targets[ac])}, şu an {pct(weights_before[ac])}, alım sonrası {pct(weights_after[ac])}."
            ),
        )
        for ac, inst, quantity, cost in bought
    )

    if split.to_emergency > 0:
        notes.insert(0, f"Önce acil durum fonu: {tl(split.to_emergency)} acil durum fonuna ayrılır "
                        f"(hedef {tl(split.target)}, kalan eksik {tl(split.shortfall_after)}).")
    if budget == 0:
        notes.append("Portföye dağıtılacak tutar yok.")
    if kept_cash > 0:
        notes.append(f"{tl(kept_cash)} TL nakit/likit hedefi için nakit olarak tutulur.")
    if leftover > 0:
        notes.append(f"{tl(leftover)} dağıtılamadı: bir sonraki alım birimi bu tutardan pahalı "
                     "ya da hedef/limit dolu. TL nakit olarak kalır.")
    notes.extend(pending_notes)

    return Proposal(
        status=AWAITING_REVIEW, as_of=plan.as_of, contribution=plan.contribution,
        cash_available_before=val.cash_available, emergency=split, budget=budget,
        purchases=purchases, kept_cash=kept_cash, remaining_cash=leftover,
        pending_cash=val.cash_pending, total_before=total_before, total_after=total,
        weights_before=weights_before, weights_after=weights_after, targets=targets,
        breaches_before=breaches_before,
        breaches_after=tuple(find_breaches(plan, inst_after, class_after, total)),
        alerts_after=tuple(deviation_alerts(plan, weights_after, total)),
        notes=tuple(notes), blockers=(),
    )


__all__ = ["AWAITING_REVIEW", "BLOCKED", "Proposal", "Purchase", "allocate", "proportional_fill"]
