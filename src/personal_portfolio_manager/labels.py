"""Turkish display labels and number formatting for human-facing text."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from .data.models import AssetClass

CLASS_LABELS: dict[AssetClass, str] = {
    AssetClass.EQUITY: "Hisse",
    AssetClass.GOLD: "Altın",
    AssetClass.FX: "Döviz",
    AssetClass.TRY_LIQUID: "TL nakit/likit",
    AssetClass.SILVER: "Gümüş",
}

_CENT = Decimal("0.01")


def tl(amount: Decimal) -> str:
    """1234567.891 -> '₺1.234.567,89'."""
    q = amount.quantize(_CENT, rounding=ROUND_HALF_UP)
    text = f"{q:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"₺{text}"


def pct(fraction: Decimal) -> str:
    """0.1234 -> '%12,34'."""
    q = (fraction * 100).quantize(_CENT, rounding=ROUND_HALF_UP)
    return f"%{q}".replace(".", ",")


def qty(amount: Decimal) -> str:
    text = format(amount.normalize(), "f")
    return text.replace(".", ",")
