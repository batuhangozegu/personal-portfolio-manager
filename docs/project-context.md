# Project context

## Source and scope

Planning conversation: “Portföy modeli oluşturma”, ID `6aec8d3f-9be8-83ed-a40d-01ea180ab602`.

Prepared on 2026-11-07 from the user's current request and accessible planning-chat excerpts. Long assistant responses were truncated; allocation widgets did not expose their values. This is a requirements summary, not a complete transcript or endorsement of previous financial claims.

The user's latest scope decision is to create only the folder structure, README, and supporting project documentation. Do not implement the Python engine as part of this scaffold.

## Confirmed direction

- Project name: **Personal Portfolio Manager**; repository name: `personal-portfolio-manager`.
- Requested home: `C:\Users\batuh\Desktop\Projeler\personal-portfolio-manager` (verify the actual location when continuing).
- Planned BIST stock screening and explainable portfolio-aware stock recommendations, after the allocation/risk baseline and historical validation.

- Personal savings with no fixed end date.
- BIST equities, TEFAS funds, gold, silver, and FX.
- Monthly contributions plus occasional additional contributions.
- Approximately 20% temporary drawdown tolerance; this is not guaranteed protection.
- Rule-based allocation and risk management first.
- Historical backtesting before considering ML.
- Human approval of alerts and suggestions; no automated order placement.
- Prefer rebalancing through new contributions where practical.

## Draft decisions, not validated policy

The 5% single-equity limit, 15% single-fund limit, 7.5% silver limit, ±5 percentage-point deviation band, and 10%/15%/20% drawdown thresholds came from the earlier assistant's proposal. They remain research assumptions pending review and backtesting.

## Decisions still needed

1. Initial target weights by asset class and, where applicable, instrument.
2. Initial instruments, fund categories, and a definition of “risky purchase”.
3. Rules for restricted purchases, unused cash, and re-entry after a drawdown review.
4. Starting balances, monthly contribution amount, and the first input format.
5. Data sources, permitted use, timestamps, currencies, and freshness limits.
6. Treatment of fees, spreads, taxes, dividends, corporate actions, fund NAV timing, and settlement delays.
7. GitHub visibility and licensing. Do not place personal holdings in the repository.

None of these unknowns prevents the documentation scaffold. Resolve those relevant to the first feature before implementing it.

## Reusable continuation brief

> Read README.md and docs/ in the personal-portfolio-manager repository. This is a personal long-term portfolio decision-support project covering BIST, TEFAS funds, gold, silver, and FX, with monthly and occasional extra contributions. Approximate 20% drawdown tolerance is a review constraint, not a guarantee. Build a transparent rule-based baseline, then backtest before ML. All suggestions need human approval; no automated orders. The current repository is documentation and empty folders only. Confirm the next milestone before writing the engine. Do not assume the complete ChatGPT conversation or attachments are available.
