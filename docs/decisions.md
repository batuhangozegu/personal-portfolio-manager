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

## 7. Buy instruments per asset class

- Each target lists `buy_instruments` (zero or more). New money for a class is split evenly across them, each within its own cap; overflow goes to the class's other instruments.
- Consequence of the 15% single-fund and 5% single-stock caps: a 40% equity target needs at least three equity funds (or a mix of funds and stocks) to be reachable. A 20% gold or FX target held through a single fund would also hit the 15% cap; physical/gram gold and FX cash have no per-instrument cap.
- A class with no buy instrument keeps its share as TRY cash, with a note. For TRY cash/liquid that is the intended behaviour (kept cash).
- Intended equity sleeve: a basket of roughly 10–15 individually selected BIST stocks, not a single fund and not short-term trading. The basket is revised with market conditions through the stock screener (milestone 3) and portfolio-aware recommendations (milestone 5). Until then, the even split across `buy_instruments` is a placeholder for screener-driven weights.

## 8. Stocks and funds

- The equity class initially holds **direct BIST stocks only**; that basket is the project's core. Funds serve other roles (money-market fund for TRY liquid, gold/FX funds where useful).
- Selection and reporting keep stocks and funds apart (stocks via the screener; funds by their own criteria such as fees, size, track record). Risk measurement stays exposure-based, so an equity fund, if added later, still counts as equity.
- If equity funds are added later, split the equity target into sub-targets (stock basket / equity funds).

## 9. Stock screener — layer structure

Three layers: (1) eligibility filters (pass/fail), (2) scoring with established models (Piotroski F-Score, Greenblatt Magic Formula, Altman Z-Score plus supporting ratios), (3) basket construction (top 10–15, 5% single-stock cap, sector limit). Growth must be measured in real terms because of TMS 29 inflation accounting from 2023 year-end statements.

### Layer 1: eligibility filters (draft thresholds, configurable)

| # | Filter | Draft rule |
| --- | --- | --- |
| 1 | Market | Exclude Watchlist Market (Yakın İzleme Pazarı) and stocks under exchange surveillance measures (VBTS tedbir) |
| 2 | Liquidity | Top 150 by 3-month median daily traded value (rank-based, so it does not erode with inflation). BIST 100 membership was dropped, see 11.5 |
| 3 | Free float | Actual free-float ratio ≥ 20% (live screening only; skipped in backtests, see 11.6) |
| 4 | History | At least 3 years (12 quarters) of financial statements |
| 5 | Profitability | Trailing-12-month net profit > 0 **and** profitable in at least 2 of the last 3 years |
| 6 | Equity | Shareholders' equity > 0 |
| 7 | Audit | Exclude adverse, qualified or disclaimer of opinion |
| 8 | Freshness | Exclude and flag when the latest statement is older than expected |
| 9 | Sector | Initially exclude banks, insurance, factoring/leasing, REITs (GYO) and holdings; their accounting makes EBITDA/debt ratios meaningless. May return later with sector-specific rules |

### Layer 2: scoring ("gates, then rank")

1. **Safety gate:** Altman Z''-Score (emerging-market / non-manufacturing variant). Distress zone → excluded; grey zone → allowed but flagged.
2. **Quality gate:** Piotroski F-Score ≥ 6 (of 9).
3. **Ranking:** Greenblatt Magic Formula — rank by return on capital (EBIT / (net working capital + net fixed assets)) and by earnings yield (EBIT / enterprise value); order by the sum of the two ranks. Ratio-based, so relatively robust to TMS 29.
4. **Supporting ratios** (ROE, net debt/EBITDA, free cash flow, P/E, P/B) are shown as explanation only and do not enter the score, to keep it explainable and limit overfitting in backtests.

Each gate and the ranking are evaluated separately in backtesting (milestone 4).

### Layer 3: basket construction

| # | Topic | Rule |
| --- | --- | --- |
| 1 | Size | Target 12 stocks (range 10–15) |
| 2 | Too few candidates | Do not relax rules to fill the basket; hold fewer stocks, leave the unfilled equity share in cash and report it |
| 3 | Weighting | Equal weight within the basket |
| 4 | Sector limit | At most 3 stocks per sector |
| 5 | Review cadence | Quarterly, after the financial-statement season |
| 6 | Hysteresis | A new stock enters only from the top 12; a held stock stays while it ranks in the top 25 and passes the gates |
| 7 | Leaving the basket | New purchases stop; the stock is marked "hold, do not add" unless a sell trigger below applies |

### Sell proposals (always require human approval)

The allocation engine still never sells to rebalance. Sales are proposed only on these triggers:

| Priority | Trigger | Proposal |
| --- | --- | --- |
| Urgent | Altman Z'' in distress zone, negative equity, adverse audit opinion, or moved to the Watchlist Market | Sell the whole position |
| High | F-Score ≤ 3, or trailing-12-month net loss | Sell the whole position |
| Normal | Outside the top 25 for **2 consecutive** quarterly reviews | Consider selling; redirect proceeds to the basket |
| Normal | Position above 1.5× the single-stock cap (7.5%) | Trim back to the 5% cap |

Not sell triggers: a price decline alone (no stop-loss), a single quarter's rank drop, short-term news.

Every sell proposal states the triggering rule and data, estimated commission, settlement date (proceeds are unusable until T+2) and where the proceeds would go under the same allocation rules. The system never places orders.

## 10. Starting state

- Starting from an empty portfolio. The first contribution is allocated directly by target weights; later contributions close deviations.
- Instrument-level selection (which funds/equities) is deferred; the MVP can operate at asset-class level first.

## 11. Data sources (milestone 2)

Agreed on 2026-11-12. One data type at a time. **Only free sources are used** (see 11.5).

### 11.1 Financial statements: KAP (Public Disclosure Platform)

- **Source:** the public KAP website, which states that current and historical disclosures are freely accessible. Every disclosure carries a publication timestamp, so statements can be used point-in-time: a backtest may only see a statement after its publication time.
- **Not used:** the official KAP data distribution REST API, which requires a data distribution agreement with Borsa İstanbul and MKK authorization (aimed at data vendors). Also not used as a primary source: unofficial broker endpoints without publication dates; they may serve only as a cross-check.
- **Low-volume access only.** KAP asks that high-volume requests go through the API, not the website. Therefore:
  - restrict fetching to the screener universe (about 150 liquid companies, see filter 2);
  - throttle requests (several seconds apart) and spread the one-time historical backfill over several days;
  - cache every downloaded file locally and never download it twice; quarterly updates fetch only new disclosures.
- **Raw data stays out of version control.** The repository is public; it shares code, not KAP data.
- **Own thin client.** Existing open-source wrappers (e.g. PyKap, MIT) are reference material only, so that publication timestamps and caching stay under our control.
- **Open questions:** no explicit KAP terms-of-use or reuse licence text was found, and the first year of structured (XBRL/Excel) statements was not verified; check both before the backfill.

### 11.2 Prices and traded volume: Yahoo Finance, checked against KAP

- **Primary source:** Yahoo Finance daily data (`.IS` tickers) for personal, non-commercial use. **Cross-check:** İş Yatırım's public price data. Both are unofficial; the official Borsa İstanbul feed is licensed for data vendors and is not used.
- **Corporate actions come from KAP.** Bonus issues (bedelsiz), rights issues and dividends are read from KAP disclosures with the same client as 11.1. On every bonus-issue date the price series is checked for an unexplained jump; mismatches are **flagged, never silently patched**.
- **Market value from KAP data:** share count is derived from paid-in capital in the statements, so market cap = price × shares and EV = market cap + net debt, without relying on the price vendor's fundamentals.
- **Known gap:** delisted stocks are usually missing from free price sources, so backtests carry survivorship bias. Reports state this explicitly; results are treated as optimistic.
- Same access rules as 11.1: low volume, local cache, raw data out of version control.

### 11.3 Macro and FX: TCMB EVDS

- **Single source:** the Central Bank's EVDS service (official, free, requires registration and an API key) for monthly CPI (TÜFE, published by TÜİK and served via EVDS), daily USD/TRY and EUR/TRY, and policy/deposit rates.
- **FX convention:** TCMB indicative buying rate (announced daily at 15:30) for dated conversions of foreign-currency holdings.
- **Point-in-time rule:** a month's CPI becomes visible to backtests only from the 5th day of the following month (a simple, conservative publication lag).
- **Secrets:** the API key lives in a local, git-ignored `.env`; `.env.example` gets only an empty `EVDS_API_KEY=` line when the client is implemented.

### 11.4 Funds, gold and silver

- **Funds:** daily prices from TEFAS (Takasbank's official fund platform), which publishes historical prices free of charge. There is no public official API; only the handful of held or candidate funds are fetched, with the same low-volume and caching rules as 11.1.
- **Fund price timing:** a fund's price is published at the end of the day and orders execute at a forward price; backtests must not trade at the same day's price (modelled in milestone 4).
- **Gram gold and silver:** derived, not sourced: gram price (TRY) = ounce price (USD) / 31.1035 × USD/TRY, with the ounce price from Yahoo (11.2) and USD/TRY from EVDS (11.3). Bank buy/sell spreads differ from this mid price and are modelled as a cost in milestone 4.

### 11.5 Free sources only

- Paid subscriptions and licensed data feeds are out of scope. A free source is used when its access is allowed; if a criterion needs data that cannot be obtained free, the criterion is removed rather than approximated.
- Applied: **BIST 100 membership is dropped from the liquidity filter.** Point-in-time historical index constituents are not freely available, and using today's list in backtests would leak future information. The rank by median traded value, computed from 11.2 data at each date, covers the same purpose.

### 11.6 Market status and free float

| Data | Free source | History | Use |
| --- | --- | --- | --- |
| Volatility-based measures (VBTS tedbir) | Borsa İstanbul announcements on KAP | Yes, with publication time | Filter 1, via the KAP client (11.1) |
| Watchlist Market (Yakın İzleme Pazarı) transfers | Expected to be Borsa İstanbul announcements on KAP; **not yet verified** | Yes, if on KAP | Filter 1 if verified; otherwise the criterion is removed (11.5) |
| Free-float ratio | MKK, published free on KAP company pages and VAP | **No.** MKK changed the method in September 2026 and now publishes daily; earlier ratios are not comparable | Filter 3 in live screening only |

- In backtests the free-float filter is **disabled and reported as such**; applying today's ratio to past dates would leak future information.
