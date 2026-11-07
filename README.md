# Personal Portfolio Manager

A personal, long-term investment portfolio decision-support project for an investor in Türkiye.

Rule-based portfolio allocation, risk monitoring, and explainable BIST stock research.

**Status: project scaffold. No investment engine, live data connection, backtest, or trading integration has been implemented.**

## Purpose

Build an explainable, rule-based process for reviewing a mixed portfolio and directing monthly and occasional extra contributions. Start with allocation and risk management, validate with historical backtests, and consider machine learning only after establishing a reliable baseline.

The intended investment universe includes:

- BIST-listed equities.
- TEFAS investment funds, with exposure classified by fund strategy.
- Gold and silver.
- Foreign currency holdings.
- TRY cash as an explicit allocation and liquidity category.

Reporting will use TRY as the initial base currency. Currency conversion must use dated rates. Nominal TRY gains and changes in purchasing power must be reported separately once inflation data is available.

## Investor context

- Open-ended investment horizon: saving for the future.
- Regular monthly contributions and additional contributions when available.
- Approximate tolerance for a temporary 20% portfolio drawdown.
- Alerts and suggestions require human review; the project will not place investment orders.

**The 20% figure expresses risk tolerance, not a guaranteed loss limit.** Proposed rules, asset weights, and historical results cannot guarantee a future drawdown ceiling. No target portfolio weights have been approved.

## Proposed MVP

1. Accept a manually entered portfolio snapshot, target weights, and new contribution amount.
2. Calculate total value, current weights, and deviations from target weights.
3. Suggest how new contributions could reduce underweights, without requiring sales.
4. Check concentration limits and drawdown review thresholds.
5. Produce an explanation of each suggestion and any unallocated cash for human approval.

Monthly and extra contributions will use the same allocation rules. A falling price alone will not trigger a buy suggestion. Missing or stale data must be visible and must prevent actionable suggestions where required inputs are unavailable.

## Draft risk rules

These draft risk rules apply to both allocation and future stock recommendations.

These are **research assumptions carried forward from the planning conversation**, not calibrated or validated investment rules:

| Parameter | Draft assumption |
| --- | --- |
| Single BIST equity | Maximum 5% of portfolio |
| Single fund | Normally maximum 15%; any exception must be explicitly reviewed |
| Silver exposure | Maximum 7.5% of portfolio |
| Allocation review | Monthly and on an extra contribution |
| Allocation deviation | Review at ±5 percentage points from target |
| Drawdown reaches 10% | Risk review alert |
| Drawdown reaches 15% | Restrict new risky purchases pending review |
| Drawdown reaches 20% | Urgent review and risk-reduction suggestions |

Thresholds generate review decisions, not automatic sale orders. Drawdown should be calculated from a cash-flow-adjusted performance series so that deposits do not hide losses. Fund and direct holdings may overlap; look-through exposure analysis is planned, not implemented.

## Planned BIST stock research

After the allocation and risk MVP, a stock screener will evaluate BIST companies using profitability, debt, cash flow, valuation, and financial-statement trends. It will produce a research shortlist with reasons, risks, source dates, and missing-data flags.

After historical validation, portfolio-aware recommendations may identify candidates to consider, hold, or avoid adding to, using the investor's existing exposure and risk limits. A strong company score must not override a portfolio concentration limit or a risk restriction. Recommendations require human review and do not imply guaranteed returns or reliable price prediction.

Historical tests must use financial statements as they were actually available at each decision date. The screener and recommendation engine are planned features, not implemented capabilities.

## Folder structure

```text
personal-portfolio-manager/
├── README.md
├── .gitignore
├── .env.example
├── docs/
│   ├── project-context.md
│   ├── architecture.md
│   └── roadmap.md
├── examples/                  # Future synthetic inputs only
├── src/
│   └── personal_portfolio_manager/
│       ├── portfolio/         # Valuation, weights, deviations
│       ├── risk/              # Limits and risk review states
│       ├── strategies/        # Contribution allocation rules
│       ├── research/          # Future BIST screening and stock research
│       ├── data/              # Input validation and provider adapters
│       └── backtesting/       # Historical evaluation after the MVP
└── tests/                    # Future tests alongside implementation
```

Empty directories contain `.gitkeep` placeholders. There is currently nothing to install or run. Python packaging, dependencies, and automated checks will be added with the first implementation milestone.

## Development order

See [the roadmap](docs/roadmap.md) for acceptance criteria and [the architecture](docs/architecture.md) for module boundaries. Confirm target weights and data conventions before implementing allocation logic.

## Privacy and scope

Use synthetic examples in version control. Keep actual balances, account exports, credentials, and local datasets outside tracked files. `.gitignore` is a convenience, not a guarantee: inspect staged files before committing.

Live market data, broker connections, automated orders, tax calculations, notifications to external services, and ML models are outside the initial scope. No tax assumptions from the planning chat have been adopted as verified rules.
