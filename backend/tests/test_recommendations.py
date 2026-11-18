"""Tests for the rule and trend based suggestions."""

from app.intelligence.financial_health import calculate_financial_health
from app.intelligence.recommendations import MAX_ITEMS, build_recommendations, inr
from factories import record, reserve


def ids(result: dict) -> list[str]:
    return [item["id"] for item in result["recommendation_items"]]


def months(*values: tuple[str, float, float]) -> list[dict]:
    """Build income + expense records from (month, income, expense) tuples."""
    rows = []
    for when, income, expense in values:
        rows += [record("income", when, income), record("expense", when, expense)]
    return rows


def test_inr_uses_indian_grouping() -> None:
    assert inr(999) == "₹999"
    assert inr(1000) == "₹1,000"
    assert inr(230000) == "₹2,30,000"
    assert inr(12345678) == "₹1,23,45,678"
    assert inr(-5000) == "-₹5,000"


def test_empty_data_prompts_first_entry() -> None:
    assert ids(calculate_financial_health([], [])) == ["data.none"]


def test_watch_level_indicators_now_get_suggestions() -> None:
    # Savings rate 12.4% and reserve coverage 2.6 months are both "watch": the old rules said nothing.
    records = months(("2026-08", 85000, 52000), ("2026-09", 88000, 58000), ("2026-10", 94000, 61000))
    records += [record("savings", m, v) for m, v in [("2026-08", 10000), ("2026-09", 8000), ("2026-10", 15000)]]
    reserves = [reserve("2026-08", 140000), reserve("2026-09", 150000), reserve("2026-10", 162000)]
    result = calculate_financial_health(records, reserves)
    found = ids(result)
    assert "savings_rate.watch" in found
    assert "financial_reserve_coverage.watch" in found
    assert "trend.expenses_rising" in found
    assert "data.keep_recording" not in found
    assert all(isinstance(m, str) for m in result["recommendations"])
    assert len(result["recommendations"]) == len(result["recommendation_items"])


def test_attention_items_come_first_and_list_is_capped() -> None:
    records = months(("2026-08", 50000, 48000), ("2026-09", 30000, 49000), ("2026-10", 20000, 52000))
    records += [record("debt", m, 300000, payment=25000) for m in ("2026-08", "2026-09", "2026-10")]
    result = calculate_financial_health(records, [reserve("2026-10", 10000)])
    items = result["recommendation_items"]
    assert len(items) <= MAX_ITEMS
    severities = [i["severity"] for i in items]
    order = {"attention": 0, "watch": 1, "info": 2, "positive": 3}
    assert severities == sorted(severities, key=order.__getitem__)
    assert severities[0] == "attention"
    assert "trend.latest_month_deficit" in ids(result)


def test_income_falling_trend() -> None:
    result = calculate_financial_health(months(("2026-08", 60000, 20000), ("2026-09", 55000, 20000), ("2026-10", 50000, 20000)), [])
    assert "trend.income_falling" in ids(result)


def test_tiny_changes_are_not_called_trends() -> None:
    result = calculate_financial_health(months(("2026-08", 50000, 30000), ("2026-09", 50000, 30100), ("2026-10", 50000, 30200)), [])
    assert "trend.expenses_rising" not in ids(result)


def test_trends_need_three_months() -> None:
    result = calculate_financial_health(months(("2026-09", 50000, 20000), ("2026-10", 40000, 30000)), [])
    found = ids(result)
    assert "trend.income_falling" not in found
    assert "trend.expenses_rising" not in found
    assert "data.few_months" in found


def test_positive_notes_are_limited_to_two() -> None:
    records = months(("2026-08", 100000, 40000), ("2026-09", 100000, 40000), ("2026-10", 100000, 40000))
    records += [record("savings", m, 30000) for m in ("2026-08", "2026-09", "2026-10")]
    reserves = [reserve("2026-08", 200000), reserve("2026-09", 230000), reserve("2026-10", 260000)]
    result = calculate_financial_health(records, reserves)
    positives = [i for i in result["recommendation_items"] if i["severity"] == "positive"]
    assert len(positives) == 2
    assert positives[0]["id"] == "trend.reserves_growing"


def test_missing_data_prompts() -> None:
    records = [record("income", "2026-08", 50000), record("expense", "2026-09", 20000),
               record("debt", "2026-08", 10000, payment=None)]
    found = ids(calculate_financial_health(records, []))
    assert {"data.no_reserves", "data.expenses_without_income", "data.debt_payment_missing", "data.few_months"} <= set(found)


def test_build_recommendations_never_returns_empty() -> None:
    indicators = [{"name": "savings_rate", "value": None, "status": "limited_data"}]
    monthly = [{"month": "2026-08", "income": 1.0, "expenses": 0.5, "savings": None, "debt_balance": None, "debt_payment": None, "reserve": 1.0}] * 3
    items = build_recommendations(indicators, monthly, 3)
    assert items
