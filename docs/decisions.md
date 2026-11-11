# MVP decisions

Agreed on 2026-11-11 for the deterministic allocation MVP (roadmap milestone 1). These are starting conventions, not validated investment policy. Values that are configuration should live in the input file, not in code, so they can be revised after backtesting.

## 1. Input format: JSON

- Inputs (snapshot, instruments, targets, limits, contribution) are JSON files.
- Validated with an explicit schema (Pydantic planned).
- Chosen because a future UI will exchange JSON natively; YAML's hand-editing advantage fades once a UI exists, and CSV cannot represent the nested structure.

## 2. Risk limits: keep the drafts

The draft limits in the README are adopted as initial configuration values: single BIST equity 5%, single fund 15%, silver 7.5%, ±5 pp deviation band, drawdown review thresholds 10% / 15% / 20%. To be calibrated by backtesting (milestone 4).

## 3. Rounding and remaining cash

- Each instrument declares a `min_increment` (purchasable unit). Initial conventions:
  - BIST equity: 1 share.
  - TEFAS fund: configurable per instrument (broker-dependent).
  - Gold / silver: 0.01 gram.
  - FX: 0.01 unit.
- Cash that cannot be allocated stays as TRY cash and is reported with a reason.
- Invariant: sum of proposed purchases + remaining cash == contribution, exactly (decimal arithmetic).
- A purchase that would breach a limit is skipped; the amount moves to the next most-underweight eligible class.

## 4. Settlement (takas) rule

- Sale proceeds are not spendable until settlement. Each instrument declares `settlement_days` (e.g. BIST equities T+2; TEFAS funds vary by fund, roughly T+0/T+1 for money-market funds, around T+2 for equity funds, T+3 or more for some foreign funds).
- Cash is split into **available** and **pending settlement** (with value date).
- Allocation proposals use available cash only; pending cash is shown with its value date.

## 5. Target weights (asset-class level)

Weights are measured by **economic exposure**, not by vehicle: an equity fund counts as equity, a gold fund as gold.

| Asset class | Target | Includes |
| --- | --- | --- |
| Equity | 40% | Direct BIST equities, equity funds |
| Gold | 20% | Physical/gram gold, gold funds |
| FX | 20% | USD/EUR holdings, FX funds |
| TRY cash / liquid | 15% | TRY cash, money-market funds |
| Silver | 5% | Below the 7.5% cap |

Rationale: a 40% equity decline alone implies roughly a 16% portfolio impact, leaving room under the 20% tolerance; gold and FX have historically tended to offset TRY weakness. Not a guarantee; to be tested in milestone 4.

## 6. Emergency fund is separate from the portfolio

- The emergency fund is held in liquid instruments (e.g. money-market funds or FX) but is **not** part of the investment portfolio.
- Every holding carries a bucket tag: `portfolio` or `emergency`. Only `portfolio` holdings count toward weights, deviations, limits and drawdown.
- The same instrument type (e.g. a money-market fund) can appear in both buckets; the tag, not the instrument, decides where it counts.
- Target size = `monthly_expense` × `months`. Initial value: `months` = 6. Both are configuration (JSON now, editable from the future UI), so the target follows changes in living costs.
- Contribution priority: while the emergency fund is below target, contributions go to it first (up to the shortfall); only the remainder goes to the portfolio. If the fund is drawn down, refilling it takes priority again.
- The allocation report shows the emergency fund's current balance, target and shortfall separately from portfolio weights.

## 7. Starting state

- Starting from an empty portfolio. The first contribution is allocated directly by target weights; later contributions close deviations.
- Instrument-level selection (which funds/equities) is deferred; the MVP can operate at asset-class level first.
