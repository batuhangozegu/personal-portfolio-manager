"""Validated input schema for an allocation run.

All money and quantities are ``Decimal``. See docs/decisions.md for the
conventions encoded here (buckets, settlement, min increments, targets).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Positive = Annotated[Decimal, Field(gt=0)]
NonNegative = Annotated[Decimal, Field(ge=0)]
Fraction = Annotated[Decimal, Field(ge=0, le=1)]
CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]

BASE_CURRENCY = "TRY"


class AssetClass(str, Enum):
    """Economic exposure class (an equity fund counts as EQUITY)."""

    EQUITY = "equity"
    GOLD = "gold"
    FX = "fx"
    TRY_LIQUID = "try_liquid"
    SILVER = "silver"


class InstrumentKind(str, Enum):
    """Vehicle type; drives per-instrument concentration caps."""

    STOCK = "stock"
    FUND = "fund"
    COMMODITY = "commodity"
    CURRENCY = "currency"


class Bucket(str, Enum):
    """Which pot a holding belongs to. Only PORTFOLIO counts toward weights."""

    PORTFOLIO = "portfolio"
    EMERGENCY = "emergency"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FxRate(_Model):
    currency: CurrencyCode
    rate_to_try: Positive
    as_of: date
    source: str = Field(min_length=1)


class Instrument(_Model):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: InstrumentKind
    asset_class: AssetClass
    currency: CurrencyCode = BASE_CURRENCY
    price: Positive
    price_as_of: date
    min_increment: Positive
    settlement_days: int = Field(ge=0)


class Holding(_Model):
    instrument_id: str = Field(min_length=1)
    quantity: Positive
    bucket: Bucket = Bucket.PORTFOLIO


class CashBalance(_Model):
    """TRY cash. ``available_on`` after the plan date means pending settlement."""

    amount: Positive
    bucket: Bucket = Bucket.PORTFOLIO
    available_on: date | None = None
    note: str = ""


class Target(_Model):
    asset_class: AssetClass
    weight: Fraction
    buy_instrument: str | None = None


class Limits(_Model):
    max_single_stock: Fraction = Decimal("0.05")
    max_single_fund: Fraction = Decimal("0.15")
    max_asset_class: dict[AssetClass, Fraction] = Field(
        default_factory=lambda: {AssetClass.SILVER: Decimal("0.075")}
    )
    deviation_band: Fraction = Decimal("0.05")
    max_price_age_days: int = Field(default=3, ge=0)


class EmergencyFund(_Model):
    monthly_expense: NonNegative
    months: int = Field(default=6, ge=0)

    @property
    def target(self) -> Decimal:
        return self.monthly_expense * self.months


class Plan(_Model):
    as_of: date
    base_currency: Literal["TRY"] = BASE_CURRENCY
    contribution: NonNegative
    fx_rates: list[FxRate] = Field(default_factory=list)
    instruments: list[Instrument]
    holdings: list[Holding] = Field(default_factory=list)
    cash: list[CashBalance] = Field(default_factory=list)
    targets: list[Target]
    limits: Limits = Field(default_factory=Limits)
    emergency_fund: EmergencyFund | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> Plan:
        errors: list[str] = []

        ids = [i.id for i in self.instruments]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            errors.append(f"duplicate instrument ids: {dupes}")
        by_id = {i.id: i for i in self.instruments}

        for inst in self.instruments:
            if inst.price_as_of > self.as_of:
                errors.append(f"{inst.id}: price_as_of {inst.price_as_of} is after plan date")

        currencies = [r.currency for r in self.fx_rates]
        if BASE_CURRENCY in currencies:
            errors.append("fx_rates must not contain the base currency TRY")
        if len(set(currencies)) != len(currencies):
            errors.append("duplicate fx_rates currencies")
        for rate in self.fx_rates:
            if rate.as_of > self.as_of:
                errors.append(f"fx rate {rate.currency}: as_of is after plan date")
        needed = {i.currency for i in self.instruments} - {BASE_CURRENCY}
        missing_fx = sorted(needed - set(currencies))
        if missing_fx:
            errors.append(f"missing fx rates for: {missing_fx}")

        seen: set[tuple[str, Bucket]] = set()
        for h in self.holdings:
            if h.instrument_id not in by_id:
                errors.append(f"holding references unknown instrument {h.instrument_id!r}")
            key = (h.instrument_id, h.bucket)
            if key in seen:
                errors.append(f"duplicate holding {h.instrument_id!r} in bucket {h.bucket.value}")
            seen.add(key)

        classes = [t.asset_class for t in self.targets]
        if len(set(classes)) != len(classes):
            errors.append("duplicate target asset classes")
        total = sum((t.weight for t in self.targets), Decimal(0))
        if total != Decimal(1):
            errors.append(f"target weights must sum to exactly 1, got {total}")
        for t in self.targets:
            if t.buy_instrument is None:
                continue
            inst = by_id.get(t.buy_instrument)
            if inst is None:
                errors.append(f"target {t.asset_class.value}: unknown buy_instrument {t.buy_instrument!r}")
            elif inst.asset_class != t.asset_class:
                errors.append(
                    f"target {t.asset_class.value}: buy_instrument {inst.id!r} "
                    f"is {inst.asset_class.value}"
                )

        if errors:
            raise ValueError("; ".join(errors))
        return self

    def instrument(self, instrument_id: str) -> Instrument:
        for inst in self.instruments:
            if inst.id == instrument_id:
                return inst
        raise KeyError(instrument_id)

    def fx_rate(self, currency: str) -> Decimal:
        if currency == BASE_CURRENCY:
            return Decimal(1)
        for rate in self.fx_rates:
            if rate.currency == currency:
                return rate.rate_to_try
        raise KeyError(currency)

    def price_try(self, instrument: Instrument) -> Decimal:
        return instrument.price * self.fx_rate(instrument.currency)

    def target_weight(self, asset_class: AssetClass) -> Decimal:
        for t in self.targets:
            if t.asset_class == asset_class:
                return t.weight
        return Decimal(0)
