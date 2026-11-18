"""Small helpers for building record dicts and API payloads in tests."""

from calendar import monthrange
from datetime import date
from decimal import Decimal


def month(value: str) -> tuple[date, date]:
    year, mon = (int(part) for part in value.split("-"))
    return date(year, mon, 1), date(year, mon, monthrange(year, mon)[1])


def record(kind: str, when: str, amount: float, *, payment: float | None = None, category: str = "General") -> dict:
    start, end = month(when)
    return {
        "kind": kind, "period_start": start, "period_end": end, "amount": Decimal(str(amount)),
        "category": category, "required_payment": Decimal(str(payment)) if payment is not None else None,
    }


def reserve(when: str, amount: float) -> dict:
    start, end = month(when)
    return {"period_start": start, "period_end": end, "amount": Decimal(str(amount))}


def payload(when: str, amount: float, **extra) -> dict:
    start, end = month(when)
    return {"period_start": start.isoformat(), "period_end": end.isoformat(), "amount": amount, **extra}
