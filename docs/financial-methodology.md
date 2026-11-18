# Baseline financial indicators

This is an educational, configurable heuristic framework. Its labels and threshold bands are not scientifically validated credit-risk thresholds and must not be used to make lending decisions. It does not estimate default probability.

## Reporting rules

- The current UI records one complete calendar month at a time and accepts INR only.
- Multiple income, expense, savings, or debt categories can be entered for the same month. Their amounts are summed by month.
- Savings records mean contributions made during the month. Liquid reserve records mean a month-end balance; they are separate inputs.
- A month without a record is missing information, not a zero value. Ratios use matched periods where the required inputs exist.
- Debt-to-income uses required monthly debt payments divided by income, not the outstanding balance. A debt payment is required when a debt row is entered.

## Formulas

| Indicator | Calculation | Data handling |
|---|---|---|
| Average monthly income | Mean of reported monthly income totals | Only months with income records |
| Income variability | Population standard deviation of monthly income / mean monthly income | Requires at least two months and positive mean |
| Average monthly expenses | Mean of reported monthly expense totals | Only months with expense records |
| Savings rate | Sum of savings contributions / sum of income | Matched months; positive total income required |
| Expense-to-income | Sum of expenses / sum of income | Matched months; positive total income required |
| Debt-payment-to-income | Required payments / income | Matched months; positive total income required |
| Amount after reported expenses | Mean of income less expenses | Matched months; excludes debt when reporting is incomplete |
| Cash-flow volatility | Population standard deviation of monthly income minus expenses / mean income | At least two matched months and positive average income; debt excluded because missing obligations are not zero |
| Cash-flow consistency | max(0, 1 - cash-flow volatility) | Descriptive inverse of volatility, not a validated measure |
| Liquid reserve coverage | Mean reported liquid balance / mean reported monthly expenses | Requires reserve and expense data and positive average expenses |
| Average recorded debt balance | Mean of reported monthly debt balances | Only months with debt records; no debt records are not treated as zero debt |

Configurable threshold bands are in `backend/app/intelligence/financial_health.py`. Assessment categories are descriptive only. Recommendations are simple prompts based on reported indicators, not personalized financial advice.

## Suggestions (methodology `baseline-heuristic-v2`)

Suggestions are generated in `backend/app/intelligence/recommendations.py`. They are short, descriptive prompts, not personalised financial advice. Each has a severity: **attention**, **watch**, **info** (more data would help) or **positive**. They are sorted in that order, trend warnings come before threshold warnings within a severity, and at most five are shown.

| Source | Rule | Severity |
|---|---|---|
| Threshold | Income variability, cash-flow volatility, savings rate, expense-to-income, debt-payment-to-income or reserve coverage is in its "watch" or "attention" band | watch / attention |
| Threshold | Reserve coverage, savings rate, debt-payment-to-income, expense-to-income or income variability is favourable (at most two positive notes in total) | positive |
| Trend | Expenses rose in each of the last 3 reported months and by at least 5% overall | watch |
| Trend | Income fell in each of the last 3 reported months and by at least 5% overall | watch |
| Trend | In the latest month with both income and expenses, expenses were higher than income | attention |
| Trend | Month-end reserves rose (positive) or fell (watch) for 3 reported months, by at least 5% | positive / watch |
| Trend | Savings contributions above zero in each of the last 3 reported months | positive |
| Data | No records; fewer than 3 months; no reserve balances; expenses without income in a month; a debt without a required payment | info |

Trends use the last three *reported* months for each series; a month without a value for that series is skipped, not treated as zero. If no rule applies, the message "Keep recording complete monthly information…" is shown.

Saved assessments store both the plain messages and the structured items. Snapshots saved under `baseline-heuristic-v1` only have plain messages, which the UI shows as neutral items.
