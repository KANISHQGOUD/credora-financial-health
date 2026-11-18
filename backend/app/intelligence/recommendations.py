"""Plain-language suggestions built from the baseline indicators and monthly series.

These are descriptive prompts, not personalised financial advice. Each item has:

- ``id``: stable identifier for the rule that produced it
- ``severity``: ``attention`` | ``watch`` | ``info`` | ``positive``
- ``indicator``: the indicator name it relates to, or ``None``
- ``message``: the text shown to the borrower

Items are ordered by severity and capped at ``MAX_ITEMS``.
"""

from datetime import date
from typing import Any

SEVERITY_ORDER = {"attention": 0, "watch": 1, "info": 2, "positive": 3}
MAX_ITEMS = 5
MAX_POSITIVE = 2
TREND_MONTHS = 3
TREND_MIN_CHANGE = 0.05  # ignore "trends" smaller than 5% end to end
FALLBACK_MESSAGE = "Keep recording complete monthly information to make these descriptive indicators more useful over time."


def inr(value: float) -> str:
    """Format a rupee amount with Indian digit grouping, e.g. 1234567 -> ₹12,34,567."""
    sign = "-" if value < 0 else ""
    digits = str(int(round(abs(value))))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups + [tail])
    return f"{sign}₹{digits}"


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def _month_label(key: str) -> str:
    year, month = (int(part) for part in key.split("-"))
    return date(year, month, 1).strftime("%b %Y")


def _item(rule_id: str, severity: str, message: str, indicator: str | None = None) -> dict[str, Any]:
    return {"id": rule_id, "severity": severity, "indicator": indicator, "message": message}


# Messages for each indicator by status. ``{v}`` is the formatted indicator value.
INDICATOR_MESSAGES: dict[str, dict[str, str]] = {
    "income_variability": {
        "attention": "Your income changed a lot from month to month (about {v} variation). Planning essential spending around your lowest recent month can make budgeting safer.",
        "watch": "Your income moves around somewhat (about {v} variation). Keeping a small buffer for lower-income months can help.",
        "favorable": "Your income has been consistent across the months you reported.",
    },
    "cash_flow_volatility": {
        "attention": "What's left after expenses swings widely between months. Noting which months run short can help you plan for them.",
        "watch": "What's left after expenses varies between months. Setting aside some of the surplus in good months can smooth this out.",
    },
    "savings_rate": {
        "attention": "You're saving about {v} of your income, under 10%. Even a small automatic transfer each payday can help build a buffer.",
        "watch": "You're saving about {v} of your income. A common rule of thumb is to work towards about 20% when you can.",
        "favorable": "You're saving about {v} of your income, above the 20% rule of thumb this tool uses.",
    },
    "expense_to_income_ratio": {
        "attention": "Expenses take about {v} of your income, leaving little room for savings or surprises. Reviewing flexible spending and recurring commitments may help.",
        "watch": "Expenses take about {v} of your income. Keeping an eye on flexible categories could free up room for saving.",
        "favorable": "Expenses use about {v} of your income, leaving room to save.",
    },
    "debt_to_income_ratio": {
        "attention": "Required debt payments take about {v} of your income. Reviewing payment dates and balances, with a qualified adviser if needed, may help.",
        "watch": "Debt payments take about {v} of your income. Avoiding new borrowing while you pay this down keeps it manageable.",
        "favorable": "Debt payments are a modest share of your income ({v}).",
    },
    "financial_reserve_coverage": {
        "attention": "Your cash reserves cover less than one month of expenses ({v}). Building a small emergency buffer over time could help.",
        "watch": "Your cash reserves cover about {v} of expenses. A common goal is three months or more.",
        "favorable": "Your cash reserves cover about {v} of expenses.",
    },
}

# Order in which favourable notes are considered (most meaningful first).
POSITIVE_PRIORITY = [
    "financial_reserve_coverage", "savings_rate", "debt_to_income_ratio", "expense_to_income_ratio", "income_variability",
]


def _format_value(name: str, value: float) -> str:
    if name == "financial_reserve_coverage":
        return f"{value:.1f} months"
    return _pct(value)


def _threshold_items(indicators: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    """Return (concerns, positives) from indicator statuses."""
    by_name = {i["name"]: i for i in indicators}
    concerns: list[dict] = []
    for name, messages in INDICATOR_MESSAGES.items():
        indicator = by_name.get(name)
        if not indicator or indicator["value"] is None:
            continue
        status = indicator["status"]
        if status in ("attention", "watch") and status in messages:
            text = messages[status].format(v=_format_value(name, indicator["value"]))
            concerns.append(_item(f"{name}.{status}", status, text, name))

    positives: list[dict] = []
    for name in POSITIVE_PRIORITY:
        indicator = by_name.get(name)
        message = INDICATOR_MESSAGES[name].get("favorable")
        if indicator and indicator["value"] is not None and indicator["status"] == "favorable" and message:
            positives.append(_item(f"{name}.favorable", "positive", message.format(v=_format_value(name, indicator["value"])), name))
    return concerns, positives


def _last(monthly: list[dict[str, Any]], key: str, count: int = TREND_MONTHS) -> list[tuple[str, float]]:
    """The last ``count`` reported values for ``key`` (months without a value are skipped)."""
    values = [(m["month"], m[key]) for m in monthly if m.get(key) is not None]
    return values[-count:] if len(values) >= count else []


def _strictly(values: list[float], rising: bool) -> bool:
    pairs = zip(values, values[1:])
    return all(b > a for a, b in pairs) if rising else all(b < a for a, b in pairs)


def _big_enough(first: float, last: float) -> bool:
    return first > 0 and abs(last - first) / first >= TREND_MIN_CHANGE


def _trend_items(monthly: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    concerns: list[dict] = []
    positives: list[dict] = []

    expenses = _last(monthly, "expenses")
    if expenses:
        values = [v for _, v in expenses]
        if _strictly(values, rising=True) and _big_enough(values[0], values[-1]):
            concerns.append(_item("trend.expenses_rising", "watch",
                                  f"Expenses have risen for {len(values)} reported months in a row ({inr(values[0])} → {inr(values[-1])}).",
                                  "average_monthly_expenditure"))

    income = _last(monthly, "income")
    if income:
        values = [v for _, v in income]
        if _strictly(values, rising=False) and _big_enough(values[0], values[-1]):
            concerns.append(_item("trend.income_falling", "watch",
                                  f"Income has fallen for {len(values)} reported months in a row ({inr(values[0])} → {inr(values[-1])}).",
                                  "average_monthly_income"))

    # Latest month where both income and expenses were reported.
    matched = [m for m in monthly if m.get("income") is not None and m.get("expenses") is not None]
    if matched and matched[-1]["expenses"] > matched[-1]["income"]:
        latest = matched[-1]
        concerns.append(_item("trend.latest_month_deficit", "attention",
                              f"In {_month_label(latest['month'])}, reported expenses ({inr(latest['expenses'])}) were higher than income ({inr(latest['income'])}).",
                              "monthly_disposable_income"))

    reserves = _last(monthly, "reserve")
    if reserves:
        values = [v for _, v in reserves]
        if _strictly(values, rising=True) and _big_enough(values[0], values[-1]):
            positives.append(_item("trend.reserves_growing", "positive",
                                   f"Your cash reserves have grown for {len(values)} reported months in a row.",
                                   "financial_reserve_coverage"))
        elif _strictly(values, rising=False) and _big_enough(values[0], values[-1]):
            concerns.append(_item("trend.reserves_shrinking", "watch",
                                  f"Your cash reserves have fallen for {len(values)} reported months in a row ({inr(values[0])} → {inr(values[-1])}).",
                                  "financial_reserve_coverage"))

    savings = _last(monthly, "savings")
    if savings and all(v > 0 for _, v in savings):
        positives.append(_item("trend.savings_streak", "positive",
                               f"You've saved something in each of your last {len(savings)} reported months.", "savings_rate"))
    return concerns, positives


def _missing_data_items(monthly: list[dict[str, Any]], reporting_months: int) -> list[dict]:
    items: list[dict] = []
    if reporting_months == 0:
        return [_item("data.none", "info", "Add your first month of income and expenses to see your indicators.")]
    if reporting_months < TREND_MONTHS:
        items.append(_item("data.few_months", "info",
                           f"You've reported {reporting_months} month(s). Adding at least {TREND_MONTHS} months makes the indicators more reliable and unlocks trends."))
    if not any(m.get("reserve") is not None for m in monthly):
        items.append(_item("data.no_reserves", "info",
                           "Add a month-end cash balance to see how many months of expenses your savings could cover.",
                           "financial_reserve_coverage"))
    unmatched = [m["month"] for m in monthly if m.get("expenses") is not None and m.get("income") is None]
    if unmatched:
        months = ", ".join(_month_label(m) for m in unmatched[-3:])
        items.append(_item("data.expenses_without_income", "info",
                           f"Some months have expenses but no income recorded ({months}). Adding income there lets the ratios include those months."))
    if any(m.get("debt_balance") is not None and m.get("debt_payment") is None for m in monthly):
        items.append(_item("data.debt_payment_missing", "info",
                           "A debt record is missing its required monthly payment, so debt payments can't be compared with income for that month.",
                           "debt_to_income_ratio"))
    return items


def build_recommendations(indicators: list[dict[str, Any]], monthly: list[dict[str, Any]], reporting_months: int) -> list[dict[str, Any]]:
    """Build ordered, de-duplicated suggestions from indicators and the full monthly series."""
    threshold_concerns, threshold_positives = _threshold_items(indicators)
    trend_concerns, trend_positives = _trend_items(monthly)
    positives = (trend_positives + threshold_positives)[:MAX_POSITIVE]
    # Trend warnings first: they point at a specific recent month, so they are the
    # most actionable items when the list has to be trimmed.
    items = trend_concerns + threshold_concerns + _missing_data_items(monthly, reporting_months) + positives

    seen: set[str] = set()
    unique = [i for i in items if not (i["id"] in seen or seen.add(i["id"]))]
    unique.sort(key=lambda i: SEVERITY_ORDER[i["severity"]])  # stable: keeps rule order within a severity
    if not unique:
        unique = [_item("data.keep_recording", "info", FALLBACK_MESSAGE)]
    return unique[:MAX_ITEMS]
