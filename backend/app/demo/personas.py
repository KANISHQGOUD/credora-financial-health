"""Deterministic sample data for three example borrowers.

Each persona produces six complete calendar months ending with the last finished
month, so the dashboard always looks current. Amounts follow a fixed pattern with
a small seeded jitter, so the same month always gives the same numbers.

The figures are invented for demonstration only.
"""

import random
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

GENERATOR_VERSION = "personas-v1"
MONTHS = 6


@dataclass(frozen=True)
class Persona:
    key: str
    label: str
    description: str
    seed: int


PERSONAS: dict[str, Persona] = {
    "steady": Persona("steady", "Steady salaried", "Regular salary, healthy savings and a small education loan.", 101),
    "freelancer": Persona("freelancer", "Irregular freelancer", "Income that swings month to month and a thin cash buffer.", 202),
    "stretched": Persona("stretched", "Stretched by debt", "Loan and card payments take a large share of income, and spending is rising.", 303),
}


@dataclass
class Row:
    kind: str  # income | expense | savings | debt | reserve
    period_start: date
    period_end: date
    amount: float
    category: str = "Liquid reserves"
    source_label: str = ""
    required_payment: float | None = None


@dataclass
class SampleData:
    persona: Persona
    first_month: date
    last_month: date
    rows: list[Row] = field(default_factory=list)


def last_complete_month(today: date) -> date:
    year, month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    return date(year, month, 1)


def _months_ending(last: date, count: int) -> list[date]:
    months = []
    year, month = last.year, last.month
    for _ in range(count):
        months.insert(0, date(year, month, 1))
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    return months


def _end(start: date) -> date:
    return date(start.year, start.month, monthrange(start.year, start.month)[1])


def _round(value: float, step: int = 100) -> float:
    return float(max(0, round(value / step) * step))


class _Builder:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.rows: list[Row] = []

    def jitter(self, value: float, spread: float) -> float:
        return _round(value * (1 + self.rng.uniform(-spread, spread)))

    def add(self, kind: str, month: date, amount: float, category: str = "Liquid reserves", source: str = "", payment: float | None = None) -> None:
        self.rows.append(Row(kind, month, _end(month), _round(amount), category, source, payment))


def _steady(b: _Builder, months: list[date]) -> None:
    loan, reserve = 300000.0, 170000.0
    for i, m in enumerate(months):
        b.add("income", m, 95000, "Salary", "Main employer")
        if i == 3:
            b.add("income", m, 12000, "Other income", "Festival bonus")
        b.add("expense", m, 25000, "Housing")
        b.add("expense", m, b.jitter(12000, 0.08), "Food")
        b.add("expense", m, b.jitter(4000, 0.10), "Transport")
        b.add("expense", m, b.jitter(3500, 0.10), "Utilities")
        b.add("expense", m, b.jitter(6000, 0.15), "Other expense")
        b.add("savings", m, 18000, "Investment contribution", "Monthly SIP")
        b.add("savings", m, 4000, "Emergency fund")
        b.add("debt", m, loan, "Education loan", payment=9000)
        loan -= 7000
        reserve += b.jitter(6000, 0.2)
        b.add("reserve", m, reserve)


def _freelancer(b: _Builder, months: list[date]) -> None:
    pattern = [70000, 118000, 42000, 96000, 55000, 38000]
    reserve = 30000.0
    for i, m in enumerate(months):
        income = b.jitter(pattern[i % len(pattern)], 0.05)
        b.add("income", m, income * 0.8, "Freelance", "Client projects")
        b.add("income", m, income * 0.2, "Business", "Online course sales")
        b.add("expense", m, 18000, "Housing")
        b.add("expense", m, b.jitter(11000, 0.12), "Food")
        b.add("expense", m, b.jitter(5000, 0.25), "Transport")
        b.add("expense", m, b.jitter(9000, 0.30), "Other expense", "Software and equipment")
        if income > 60000:
            b.add("savings", m, 12000, "Recurring deposit")
        b.add("debt", m, b.jitter(30000, 0.2), "Credit card", payment=3000)
        reserve += (income - 43000) * 0.1 - 3000
        b.add("reserve", m, reserve)


def _stretched(b: _Builder, months: list[date]) -> None:
    expenses = [44000, 47000, 50000, 53000, 57000, 61500]
    loan, card, reserve = 360000.0, 85000.0, 42000.0
    for i, m in enumerate(months):
        b.add("income", m, 60000, "Salary", "Retail employer")
        total = expenses[i % len(expenses)]
        b.add("expense", m, 17000, "Housing")
        b.add("expense", m, total * 0.35, "Food")
        b.add("expense", m, total * 0.12, "Transport")
        b.add("expense", m, total - 17000 - total * 0.35 - total * 0.12, "Other expense")
        b.add("savings", m, 2000, "Emergency fund")
        b.add("debt", m, loan, "Personal loan", payment=18000)
        b.add("debt", m, card, "Credit card", payment=7000)
        loan -= 11000
        card += 2500
        reserve -= 3500
        b.add("reserve", m, reserve)


GENERATORS: dict[str, Callable[[_Builder, list[date]], None]] = {
    "steady": _steady, "freelancer": _freelancer, "stretched": _stretched,
}


def generate(persona_key: str, today: date | None = None, months: int = MONTHS) -> SampleData:
    """Return the sample rows for ``persona_key``, ending with the last complete month."""
    persona = PERSONAS[persona_key]
    last = last_complete_month(today or date.today())
    month_list = _months_ending(last, months)
    builder = _Builder(random.Random(persona.seed * 10000 + last.year * 100 + last.month))
    GENERATORS[persona_key](builder, month_list)
    return SampleData(persona, month_list[0], last, builder.rows)
