"""Render a proposal as Turkish text for review, or as JSON-ready data for a UI."""

from __future__ import annotations

import dataclasses
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from .data.models import AssetClass
from .labels import CLASS_LABELS, pct, qty, tl
from .strategies.allocation import BLOCKED, Proposal


def to_dict(proposal: Proposal) -> dict[str, Any]:
    """Plain JSON-serializable data. Decimals become strings to keep precision."""

    def conv(value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, date):
            return value.isoformat()
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return {f.name: conv(getattr(value, f.name)) for f in dataclasses.fields(value)}
        if hasattr(value, "model_dump"):
            return conv(value.model_dump())
        if isinstance(value, dict):
            return {conv(k): conv(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [conv(v) for v in value]
        return value

    data = conv(proposal)
    data["purchased_total"] = str(proposal.purchased_total)
    data["review_required"] = True
    return data


def render_text(p: Proposal) -> str:
    out: list[str] = []
    status = "ENGELLENDİ" if p.status == BLOCKED else "ONAYINI BEKLİYOR"
    out.append(f"Katkı önerisi · {p.as_of} · {status}")
    out.append("Bu bir öneridir, emir değildir. Uygulamadan önce kendin kontrol et.")
    out.append("")

    if p.blockers:
        out.append("Öneri üretilemedi:")
        out += [f"  - {b}" for b in p.blockers]
        out.append("")

    out.append(f"Katkı:                  {tl(p.contribution)}")
    if p.emergency is not None:
        e = p.emergency
        if not e.configured:
            out.append("Acil durum fonu:        tanımlı değil")
        elif e.to_emergency > 0:
            out.append(f"Acil durum fonuna:      {tl(e.to_emergency)}  "
                       f"(bakiye {tl(e.balance)} / hedef {tl(e.target)}, kalan eksik {tl(e.shortfall_after)})")
        else:
            out.append(f"Acil durum fonu:        dolu ({tl(e.balance)} / hedef {tl(e.target)})")
    if p.cash_available_before > 0:
        out.append(f"Kullanılabilir nakit:   {tl(p.cash_available_before)}")
    out.append(f"Portföye dağıtılacak:   {tl(p.budget)}")
    out.append("")

    if p.purchases:
        out.append("Önerilen alımlar")
        rows = [("Enstrüman", "Miktar", "Birim fiyat", "Tutar")]
        rows += [(f"{x.instrument_name} ({x.instrument_id})", qty(x.quantity), tl(x.unit_price), tl(x.cost))
                 for x in p.purchases]
        rows.append(("Toplam", "", "", tl(p.purchased_total)))
        widths = [max(len(r[i]) for r in rows) for i in range(4)]
        for i, r in enumerate(rows):
            if i == len(rows) - 1:
                out.append("  " + "-" * (sum(widths) + 6))
            out.append("  " + r[0].ljust(widths[0]) + "  " + "  ".join(c.rjust(w) for c, w in zip(r[1:], widths[1:])))
        out.append("")
        for x in p.purchases:
            out.append(f"  · {x.instrument_id}: {x.reason}")
        out.append("")
    elif p.status != BLOCKED:
        out.append("Önerilen alım yok.")
        out.append("")

    if p.kept_cash > 0:
        out.append(f"TL nakit olarak tutulan: {tl(p.kept_cash)}")
    if p.remaining_cash > 0:
        out.append(f"Dağıtılamayan (nakitte): {tl(p.remaining_cash)}")
    if p.kept_cash > 0 or p.remaining_cash > 0:
        out.append("")

    if p.total_after > 0:
        out.append(f"Ağırlıklar (portföy {tl(p.total_before)} → {tl(p.total_after)})")
        out.append(f"  {'Sınıf':<16}{'Hedef':>9}{'Önce':>9}{'Sonra':>9}")
        for ac in AssetClass:
            out.append(f"  {CLASS_LABELS[ac]:<16}{pct(p.targets[ac]):>9}"
                       f"{pct(p.weights_before[ac]):>9}{pct(p.weights_after[ac]):>9}")
        out.append("")

    if p.breaches_before or p.breaches_after:
        out.append("Limit aşımları")
        for label, items in (("önce", p.breaches_before), ("sonra", p.breaches_after)):
            for b in items:
                out.append(f"  [{label}] {b.subject}: {pct(b.weight)} (limit {pct(b.limit)})")
        out.append("")

    if p.alerts_after:
        out.append("Sapma uyarıları (gözden geçir)")
        for a in p.alerts_after:
            sign = "+" if a.deviation > 0 else ""
            out.append(f"  {CLASS_LABELS[a.asset_class]}: {pct(a.weight)} vs hedef {pct(a.target)} "
                       f"({sign}{pct(a.deviation)})")
        out.append("")

    if p.notes:
        out.append("Notlar")
        out += [f"  - {n}" for n in p.notes]
        out.append("")

    out.append("Düşüş takibi: performans geçmişi henüz yok, risk durumu bilinmiyor.")
    return "\n".join(out)
