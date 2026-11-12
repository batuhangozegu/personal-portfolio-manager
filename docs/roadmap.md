# Roadmap

## 0. Project scaffold — done

- README, project context, proposed architecture, and development milestones.
- Empty source, test, and synthetic-example folders.
- Ignore rules and an environment configuration placeholder.
- No Python implementation, dependency installation, or live integration.

## 1. Deterministic allocation MVP — implemented, pending review

Drawdown review states are not implemented yet: they need a cash-flow-adjusted performance history, which arrives with milestone 2. The report shows the risk state as unknown.

Agree on target weights, instrument classifications, input format, risk restrictions, and rounding before coding.

Acceptance criteria:

- A synthetic snapshot yields correct total value, weights, and target deviations.
- Monthly and extra contributions use the same allocation function.
- Suggested purchases plus remaining cash equal the supplied contribution.
- Caps and purchase restrictions are respected; existing breaches are reported.
- Invalid inputs, missing history, zero contributions, and empty portfolios have explicit behavior.
- Every proposal is explainable and awaits human review.
- Tests cover arithmetic, rule boundaries, invalid inputs, and cash conservation.

## 2. Reliable historical data

**On hold:** automated access to KAP was blocked; see the project status in the README. The point-in-time store (`data/pit.py`) is implemented.

Providers are selected (free sources only; see decisions.md section 11): KAP, Yahoo Finance with İş Yatırım cross-check, TCMB EVDS, TEFAS. Remaining open checks are listed there. Normalize instruments, dated FX conversions, dividends, corporate actions, fund NAV availability, and missing data. Keep raw/private datasets out of version control.

Acceptance: a reproducible synthetic fixture and a documented historical dataset can be validated without future information leaking into past decisions.

## 3. BIST stock screener

Define transparent screening criteria for profitability, leverage, cash flow, valuation, and financial-statement trends. Use publication dates and comparable accounting periods; flag stale or incomplete inputs instead of inventing scores.

Acceptance: a reproducible shortlist explains why each company qualifies, what risks remain, and which dated sources support the assessment. This is a research shortlist, not a validated buy recommendation.

## 4. Backtesting and stress analysis

Compare a fixed allocation, contribution-only rebalancing, and the proposed risk rules under identical contribution schedules. Include fees, spreads, available tax assumptions, settlement constraints, and inflation where supported.

Acceptance: report cash-flow-adjusted performance, maximum drawdown, costs, turnover, and behavior in adverse scenarios. Separate tuning and evaluation periods. Decide whether draft limits need revision.

Evaluate the stock-screening criteria separately from allocation rules using point-in-time fundamentals and a universe that accounts for delistings. Compare results with simple baselines before enabling personalized stock recommendations.

## 5. Portfolio-aware recommendations and human-reviewed reporting

Combine validated screening results with portfolio weights, concentration limits, available cash, and risk review states. Explain candidates to consider, hold, or avoid adding to. Withhold recommendations when required data is unavailable or a risk restriction applies. No guaranteed-return or price-prediction claims.

Add local reports and an explicit review record. External notifications require a separately chosen channel and authorization. No broker order placement.

## 6. Optional ML research

Only after the rule-based baseline and historical evaluation are reliable. Define a measurable research question and require out-of-sample improvement after costs before adopting any model.
