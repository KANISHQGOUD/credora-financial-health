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
