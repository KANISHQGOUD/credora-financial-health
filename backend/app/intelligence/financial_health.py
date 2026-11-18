"""Transparent baseline financial-health calculations.

This module contains descriptive heuristics, not a validated default-risk model.
Missing observations are omitted from ratios rather than interpreted as zero.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from statistics import pstdev
from typing import Any

from app.intelligence.recommendations import build_recommendations

METHODOLOGY_VERSION = "baseline-heuristic-v2"

BASELINE_THRESHOLDS = {
    "income_variability": {"favorable_max": 0.15, "attention_above": 0.35},
    "cash_flow_volatility": {"favorable_max": 0.20, "attention_above": 0.40},
    "savings_rate": {"favorable_min": 0.20, "attention_below": 0.10},
    "expense_to_income_ratio": {"favorable_max": 0.70, "attention_above": 0.90},
    "debt_to_income_ratio": {"favorable_max": 0.25, "attention_above": 0.40},
    "financial_reserve_coverage": {"favorable_min": 3.0, "attention_below": 1.0},
}


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _money(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def _ratio_status(value: float | None, favorable: float, concern: float, *, lower_is_better: bool = True) -> str:
    if value is None:
        return "limited_data"
    if lower_is_better:
        return "favorable" if value <= favorable else "attention" if value > concern else "watch"
    return "favorable" if value >= favorable else "attention" if value < concern else "watch"


def calculate_financial_health(records: list[dict[str, Any]], reserves: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate period-aligned indicators and chart series from normalized records.

    Records or reserves carrying a ``synthetic_run_id`` came from generated sample
    data; the result is then flagged ``is_synthetic``.
    """
    is_synthetic = any(row.get("synthetic_run_id") for row in [*records, *reserves])
    periods: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "income": [], "expense": [], "savings": [], "debt_balance": [], "debt_payment": [],
        "debt_payment_complete": True, "reserve": None,
    })

    for record in records:
        start: date = record["period_start"]
        bucket = periods[start.strftime("%Y-%m")]
        kind = record["kind"]
        amount = float(record["amount"] or Decimal("0"))
        if kind == "income":
            bucket["income"].append(amount)
        elif kind == "expense":
            bucket["expense"].append(amount)
        elif kind == "savings":
            bucket["savings"].append(amount)
        elif kind == "debt":
            bucket["debt_balance"].append(amount)
            payment = record.get("required_payment")
            if payment is None:
                bucket["debt_payment_complete"] = False
            else:
                bucket["debt_payment"].append(float(payment))

    for record in reserves:
        start = record["period_start"]
        periods[start.strftime("%Y-%m")]["reserve"] = float(record["amount"])

    monthly: list[dict[str, Any]] = []
    for month in sorted(periods):
        entry = periods[month]
        monthly.append({
            "month": month,
            "income": _money(sum(entry["income"])) if entry["income"] else None,
            "expenses": _money(sum(entry["expense"])) if entry["expense"] else None,
            "savings": _money(sum(entry["savings"])) if entry["savings"] else None,
            "debt_balance": _money(sum(entry["debt_balance"])) if entry["debt_balance"] else None,
            "debt_payment": _money(sum(entry["debt_payment"])) if entry["debt_balance"] and entry["debt_payment_complete"] else None,
            "reserve": _money(entry["reserve"]),
        })

    income_months = {m["month"]: m["income"] for m in monthly if m["income"] is not None}
    expense_months = {m["month"]: m["expenses"] for m in monthly if m["expenses"] is not None}
    savings_months = {m["month"]: m["savings"] for m in monthly if m["savings"] is not None}
    debt_payment_months = {m["month"]: m["debt_payment"] for m in monthly if m["debt_payment"] is not None}
    reserve_months = {m["month"]: m["reserve"] for m in monthly if m["reserve"] is not None}
    income_values = list(income_months.values())
    income_avg = _mean(income_values)
    expense_avg = _mean(list(expense_months.values()))
    savings_avg = _mean(list(savings_months.values()))
    balance_avg = _mean([m["debt_balance"] for m in monthly if m["debt_balance"] is not None])

    income_variability = None
    if income_avg is not None and income_avg > 0 and len(income_values) >= 2:
        income_variability = pstdev(income_values) / income_avg

    expense_income_periods = sorted(set(income_months) & set(expense_months))
    expense_income_ratio = None
    if expense_income_periods:
        period_income = sum(income_months[p] for p in expense_income_periods)
        if period_income > 0:
            expense_income_ratio = sum(expense_months[p] for p in expense_income_periods) / period_income

    savings_periods = sorted(set(income_months) & set(savings_months))
    savings_rate = None
    if savings_periods:
        period_income = sum(income_months[p] for p in savings_periods)
        if period_income > 0:
            savings_rate = sum(savings_months[p] for p in savings_periods) / period_income

    debt_periods = sorted(set(income_months) & set(debt_payment_months))
    debt_to_income = None
    if debt_periods:
        period_income = sum(income_months[p] for p in debt_periods)
        if period_income > 0:
            debt_to_income = sum(debt_payment_months[p] for p in debt_periods) / period_income

    disposable_periods = sorted(set(income_months) & set(expense_months))
    disposable_income = None
    cash_flow_volatility = None
    if disposable_periods:
        net_flows = [
            income_months[p] - expense_months[p]
            for p in disposable_periods
        ]
        disposable_income = _mean(net_flows)
        if income_avg is not None and income_avg > 0 and len(net_flows) >= 2:
            cash_flow_volatility = pstdev(net_flows) / income_avg

    reserve_coverage = None
    if reserve_months and expense_avg is not None and expense_avg > 0:
        reserve_coverage = _mean(list(reserve_months.values())) / expense_avg

    indicators = [
        {"name": "average_monthly_income", "label": "Average monthly income", "value": _money(income_avg), "unit": "INR/month", "status": "available" if income_avg is not None else "limited_data", "explanation": f"Calculated from {len(income_values)} reported month(s)."},
        {"name": "income_variability", "label": "Income variability", "value": round(income_variability, 4) if income_variability is not None else None, "unit": "coefficient of variation", "status": _ratio_status(income_variability, BASELINE_THRESHOLDS["income_variability"]["favorable_max"], BASELINE_THRESHOLDS["income_variability"]["attention_above"]), "explanation": "Population standard deviation divided by average reported income; requires at least two months."},
        {"name": "average_monthly_expenditure", "label": "Average monthly expenses", "value": _money(expense_avg), "unit": "INR/month", "status": "available" if expense_avg is not None else "limited_data", "explanation": f"Calculated from {len(expense_months)} reported month(s)."},
        {"name": "savings_rate", "label": "Savings rate", "value": round(savings_rate, 4) if savings_rate is not None else None, "unit": "ratio", "status": _ratio_status(savings_rate, BASELINE_THRESHOLDS["savings_rate"]["favorable_min"], BASELINE_THRESHOLDS["savings_rate"]["attention_below"], lower_is_better=False), "explanation": "Reported savings contributions divided by income in months where both were reported."},
        {"name": "expense_to_income_ratio", "label": "Expense-to-income ratio", "value": round(expense_income_ratio, 4) if expense_income_ratio is not None else None, "unit": "ratio", "status": _ratio_status(expense_income_ratio, BASELINE_THRESHOLDS["expense_to_income_ratio"]["favorable_max"], BASELINE_THRESHOLDS["expense_to_income_ratio"]["attention_above"]), "explanation": "Total reported expenses divided by income for matched months."},
        {"name": "debt_to_income_ratio", "label": "Monthly debt-payment-to-income ratio", "value": round(debt_to_income, 4) if debt_to_income is not None else None, "unit": "ratio", "status": _ratio_status(debt_to_income, BASELINE_THRESHOLDS["debt_to_income_ratio"]["favorable_max"], BASELINE_THRESHOLDS["debt_to_income_ratio"]["attention_above"]), "explanation": "Required debt payments divided by income in months where both were reported; this is not a loan decision threshold."},
        {"name": "monthly_disposable_income", "label": "Average monthly amount after reported expenses", "value": _money(disposable_income), "unit": "INR/month", "status": "available" if disposable_income is not None else "limited_data", "explanation": "Income less expenses for matched months; excludes debt payments because unreported debt information is not assumed to be zero."},
        {"name": "cash_flow_volatility", "label": "Cash-flow volatility", "value": round(cash_flow_volatility, 4) if cash_flow_volatility is not None else None, "unit": "coefficient of variation", "status": _ratio_status(cash_flow_volatility, BASELINE_THRESHOLDS["cash_flow_volatility"]["favorable_max"], BASELINE_THRESHOLDS["cash_flow_volatility"]["attention_above"]), "explanation": "Population standard deviation of reported income minus expenses, normalized by average income; requires two matched months and excludes unreported debt payments."},
        {"name": "cash_flow_consistency", "label": "Cash-flow consistency", "value": round(max(0.0, 1.0 - cash_flow_volatility), 4) if cash_flow_volatility is not None else None, "unit": "heuristic ratio", "status": _ratio_status(max(0.0, 1.0 - cash_flow_volatility) if cash_flow_volatility is not None else None, 0.80, 0.60, lower_is_better=False), "explanation": "A simple inverse of normalized cash-flow volatility, floored at zero. It is a descriptive heuristic, not a validated stability measure."},
        {"name": "financial_reserve_coverage", "label": "Liquid reserve coverage", "value": round(reserve_coverage, 2) if reserve_coverage is not None else None, "unit": "months of reported expenses", "status": _ratio_status(reserve_coverage, BASELINE_THRESHOLDS["financial_reserve_coverage"]["favorable_min"], BASELINE_THRESHOLDS["financial_reserve_coverage"]["attention_below"], lower_is_better=False), "explanation": "Average reported liquid balance divided by average reported expenses; requires reserve and expense data."},
        {"name": "average_debt_balance", "label": "Average recorded debt balance", "value": _money(balance_avg), "unit": "INR", "status": "available" if balance_avg is not None else "limited_data", "explanation": "Average of reported debt balances. Missing debt records are not treated as zero debt."},
    ]

    available_flags = [i for i in indicators if i["status"] in {"favorable", "watch", "attention"}]
    concerns = [i for i in indicators if i["status"] == "attention"]
    overall = "More data needed" if len(available_flags) < 2 else "Needs attention" if concerns else "Steady indicators"
    recommendation_items = build_recommendations(indicators, monthly, len(monthly))

    return {
        "overall_category": overall,
        "summary": "Heuristic financial-health overview based only on information you entered. It is not a credit score or lending recommendation.",
        "indicators": indicators,
        # Plain strings kept for older clients and saved snapshots; items carry severity.
        "recommendations": [item["message"] for item in recommendation_items],
        "recommendation_items": recommendation_items,
        "monthly": monthly[-12:],
        "reporting_months": len(monthly),
        "is_synthetic": is_synthetic,
        "methodology_version": METHODOLOGY_VERSION,
    }
