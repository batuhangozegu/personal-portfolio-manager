# Proposed architecture

This document describes future module boundaries. No modules have been implemented.

## Inputs and valuation

`data/` will validate manually supplied snapshots before adding provider integrations. Each valuation needs an instrument identifier, asset class, timestamp, currency, quantity or market value, and a source. FX conversions need their own timestamp and source. Reject invalid values and identify missing or stale data.

`portfolio/` will calculate TRY values, current weights, and deviations. Target weights must sum to 100%; snapshots must avoid duplicate holdings and double-counted cash. Use decimal arithmetic for money and define rounding explicitly. Handle an empty portfolio and zero contribution without division errors.

Historical source data goes through `data/pit.py`: every observation records the period it describes and the timezone-aware moment it was published, and queries are made as of a moment, so restatements and late publications never leak into earlier decisions. Local datasets live as JSON Lines under the git-ignored `/data/` directory; `examples/pit-fixture.jsonl` is a synthetic fixture.

## Risk review

`risk/` will check instrument and asset-class concentration and derive review states from drawdown thresholds. Define fund overlap handling separately from per-instrument caps. Existing cap breaches should be reported even when new deposits dilute them.

Use a cash-flow-adjusted return index for peak-to-trough drawdown, with documented deposit and withdrawal timing. Raw account value is insufficient because contributions can conceal losses. Missing performance history must appear as an unknown risk state, not a zero drawdown.

## Contribution allocation

`strategies/` will propose allocations of new cash toward eligible target deficits. It will respect risk restrictions and caps and leave unresolved cash explicit. It will not assume a price decline is an opportunity, silently change target weights, or propose sales merely to force a match.

The proposal should contain the input snapshot reference, policy version, weights before and after, proposed amounts, remaining cash, breached rules, explanations, and a human-review status. A proposal is not an executable order.

## Historical evaluation

`research/` will hold BIST stock screening and company-level explanations based on profitability, leverage, cash flow, and valuation. Use dated source records and actual publication dates. Validate the screener historically before combining it with portfolio constraints to produce personalized recommendations. Missing fundamentals must remain explicit. This module is planned, not implemented.

`backtesting/` follows the deterministic MVP. Keep contributions separate from investment returns. Use information available at each historical decision time; account for fund NAV publication and settlement timing. Include costs and cash, benchmark against simple policies, and report both nominal TRY and inflation-adjusted outcomes where data permits.

Separate strategy tuning periods from evaluation periods. Document missing and delisted instruments, survivorship bias, corporate actions, and exposure overlap. Do not interpret a backtested drawdown below 20% as a future guarantee.

## Initial delivery interface

Prefer local file input and a local report before a dashboard or external notifications. Broker APIs, credentials, external messaging, and automated trade execution are not required for the MVP.
