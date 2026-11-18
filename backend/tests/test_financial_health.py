"""Unit tests for the baseline indicator calculations (no database needed)."""

import pytest

from app.intelligence.financial_health import _ratio_status, calculate_financial_health
from factories import record, reserve


def indicator(result: dict, name: str) -> dict:
    return next(i for i in result["indicators"] if i["name"] == name)


@pytest.fixture
def three_month_sample() -> dict:
    """The data used when testing the app by hand (Aug-Oct 2026)."""
    records = [
        record("income", "2026-08", 85000), record("income", "2026-09", 88000),
        record("income", "2026-10", 82000), record("income", "2026-10", 12000, category="Freelance"),
        record("expense", "2026-08", 52000), record("expense", "2026-09", 58000), record("expense", "2026-10", 61000),
        record("savings", "2026-08", 10000), record("savings", "2026-09", 8000), record("savings", "2026-10", 15000),
        record("debt", "2026-08", 240000, payment=12000), record("debt", "2026-09", 230000, payment=12000),
        record("debt", "2026-10", 220000, payment=12000),
    ]
    reserves = [reserve("2026-08", 140000), reserve("2026-09", 150000), reserve("2026-10", 162000)]
    return calculate_financial_health(records, reserves)


def test_sample_matches_manual_check(three_month_sample: dict) -> None:
    r = three_month_sample
    assert indicator(r, "average_monthly_income")["value"] == 89000
    assert indicator(r, "average_monthly_expenditure")["value"] == 57000
    assert indicator(r, "savings_rate")["value"] == pytest.approx(33000 / 267000, abs=1e-4)
    assert indicator(r, "debt_to_income_ratio")["value"] == pytest.approx(36000 / 267000, abs=1e-4)
    assert indicator(r, "expense_to_income_ratio")["value"] == pytest.approx(171000 / 267000, abs=1e-4)
    assert indicator(r, "financial_reserve_coverage")["value"] == pytest.approx(2.64, abs=0.01)
    assert indicator(r, "monthly_disposable_income")["value"] == 32000
    assert indicator(r, "average_debt_balance")["value"] == 230000
    assert r["reporting_months"] == 3
    assert r["overall_category"] == "Steady indicators"


def test_multiple_categories_in_a_month_are_summed(three_month_sample: dict) -> None:
    october = next(m for m in three_month_sample["monthly"] if m["month"] == "2026-10")
    assert october["income"] == 94000


def test_no_records_means_limited_data_not_zero() -> None:
    result = calculate_financial_health([], [])
    for item in result["indicators"]:
        assert item["value"] is None
        assert item["status"] == "limited_data"
    assert result["overall_category"] == "More data needed"


def test_missing_month_is_skipped_not_treated_as_zero() -> None:
    # Expenses reported for September only: income for August must not be paired with "0 expenses".
    records = [record("income", "2026-08", 50000), record("income", "2026-09", 50000), record("expense", "2026-09", 40000)]
    result = calculate_financial_health(records, [])
    assert indicator(result, "expense_to_income_ratio")["value"] == pytest.approx(0.8)
    assert indicator(result, "average_monthly_expenditure")["value"] == 40000


def test_income_variability_needs_two_months() -> None:
    assert indicator(calculate_financial_health([record("income", "2026-08", 50000)], []), "income_variability")["value"] is None
    two = calculate_financial_health([record("income", "2026-08", 40000), record("income", "2026-09", 60000)], [])
    # population stdev 10000 / mean 50000
    assert indicator(two, "income_variability")["value"] == pytest.approx(0.2)


def test_debt_without_required_payment_makes_month_incomplete() -> None:
    records = [
        record("income", "2026-08", 50000),
        record("debt", "2026-08", 100000, payment=5000),
        record("debt", "2026-08", 20000, payment=None, category="Credit card"),
    ]
    result = calculate_financial_health(records, [])
    assert indicator(result, "debt_to_income_ratio")["value"] is None
    assert indicator(result, "average_debt_balance")["value"] == 120000


def test_zero_income_does_not_divide_by_zero() -> None:
    result = calculate_financial_health([record("income", "2026-08", 0), record("expense", "2026-08", 1000)], [])
    assert indicator(result, "expense_to_income_ratio")["value"] is None


@pytest.mark.parametrize(
    ("value", "lower_is_better", "expected"),
    [
        (0.25, True, "favorable"),   # exactly at favorable max
        (0.30, True, "watch"),
        (0.40, True, "watch"),       # exactly at attention boundary is still watch
        (0.41, True, "attention"),
        (0.20, False, "favorable"),  # exactly at favorable min
        (0.15, False, "watch"),
        (0.10, False, "watch"),
        (0.09, False, "attention"),
        (None, True, "limited_data"),
    ],
)
def test_status_bands(value: float | None, lower_is_better: bool, expected: str) -> None:
    favorable, concern = (0.25, 0.40) if lower_is_better else (0.20, 0.10)
    assert _ratio_status(value, favorable, concern, lower_is_better=lower_is_better) == expected


def test_monthly_series_is_limited_to_last_twelve_months() -> None:
    records = [record("income", f"2025-{m:02d}", 1000) for m in range(1, 13)] + [record("income", "2026-01", 1000), record("income", "2026-02", 1000)]
    result = calculate_financial_health(records, [])
    assert len(result["monthly"]) == 12
    assert result["monthly"][0]["month"] == "2025-03"
    assert result["reporting_months"] == 14
