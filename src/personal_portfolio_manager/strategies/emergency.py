"""Emergency fund first: fill its shortfall before anything reaches the portfolio."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..data.models import EmergencyFund

ZERO = Decimal(0)


@dataclass(frozen=True)
class EmergencySplit:
    configured: bool
    target: Decimal
    balance: Decimal
    to_emergency: Decimal
    to_portfolio: Decimal

    @property
    def shortfall(self) -> Decimal:
        return max(ZERO, self.target - self.balance)

    @property
    def shortfall_after(self) -> Decimal:
        return max(ZERO, self.target - self.balance - self.to_emergency)


def split_contribution(
    contribution: Decimal, fund: EmergencyFund | None, balance: Decimal
) -> EmergencySplit:
    if fund is None:
        return EmergencySplit(False, ZERO, balance, ZERO, contribution)
    shortfall = max(ZERO, fund.target - balance)
    to_emergency = min(contribution, shortfall)
    return EmergencySplit(True, fund.target, balance, to_emergency, contribution - to_emergency)
