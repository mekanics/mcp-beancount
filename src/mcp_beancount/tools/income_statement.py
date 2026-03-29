"""get_income_statement tool — income vs expenses for a period."""

from __future__ import annotations

import datetime
import os
from collections import defaultdict
from typing import Any

from beancount.core import convert, prices
from beancount.core import data as beancount_data
from beancount.core.amount import Amount
from beancount.core.number import Decimal

from mcp_beancount.tools.utils import resolve_date


def get_income_statement(
    entries: list[Any],
    options: dict[str, Any],
    year: int,
    month: int | None = None,
) -> dict[str, Any]:
    """Return income and expense summary for a year or year+month period.

    In Beancount, income account postings are negative (credits). We negate
    them so that positive values represent income received.

    Args:
        entries: Beancount entries from loader.get().
        options: Beancount options dict.
        year: 4-digit year (e.g. 2026).
        month: Optional 1-12 month. If None, covers the full year.

    Returns:
        dict with: period, income_breakdown, expense_breakdown (both
        {account: {currency: float}}), total_income, total_expenses, net
        (all {currency: float}), total_income_converted and
        total_expenses_converted (scalar in base_currency).
    """
    start_date, end_date = _period_bounds(year, month)

    # Use the end_date (exclusive) minus one day as the price lookup date
    price_date = end_date - datetime.timedelta(days=1)

    # Determine base currency
    base_currency = _base_currency(options)

    # Build price map
    price_map = prices.build_price_map(entries)

    # income_breakdown: {account: {currency: Decimal}}
    income_raw: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    expense_raw: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

    for entry in entries:
        if not isinstance(entry, beancount_data.Transaction):
            continue
        if not (start_date <= entry.date < end_date):
            continue
        for posting in entry.postings:
            account = posting.account
            if posting.units is None:
                continue
            currency = posting.units.currency
            amount = posting.units.number
            if account.startswith("Income:"):
                # Income is stored as negative in beancount; negate for display
                income_raw[account][currency] += -amount
            elif account.startswith("Expenses:"):
                expense_raw[account][currency] += amount

    # Build clean breakdowns (drop zero balances, round)
    income_breakdown: dict[str, dict[str, float]] = {
        account: {c: float(round(v, 2)) for c, v in currencies.items() if v != 0}
        for account, currencies in income_raw.items()
    }
    income_breakdown = {k: v for k, v in income_breakdown.items() if v}

    expense_breakdown: dict[str, dict[str, float]] = {
        account: {c: float(round(v, 2)) for c, v in currencies.items() if v != 0}
        for account, currencies in expense_raw.items()
    }
    expense_breakdown = {k: v for k, v in expense_breakdown.items() if v}

    # Compute per-currency totals for income
    total_income: dict[str, float] = defaultdict(float)
    for per_currency in income_breakdown.values():
        for currency, amount in per_currency.items():
            total_income[currency] += amount

    # Compute per-currency totals for expenses
    total_expenses: dict[str, float] = defaultdict(float)
    for per_currency in expense_breakdown.values():
        for currency, amount in per_currency.items():
            total_expenses[currency] += amount

    # Compute net per currency
    all_currencies = set(total_income) | set(total_expenses)
    net: dict[str, float] = {
        c: round(total_income.get(c, 0.0) - total_expenses.get(c, 0.0), 2)
        for c in all_currencies
    }

    # Compute converted totals in base_currency using price_map
    total_income_converted = _convert_total(dict(total_income), base_currency, price_map, price_date)
    total_expenses_converted = _convert_total(dict(total_expenses), base_currency, price_map, price_date)

    period = f"{year:04d}-{month:02d}" if month else f"{year:04d}"

    return {
        "period": period,
        "income_breakdown": income_breakdown,
        "expense_breakdown": expense_breakdown,
        "total_income": dict(total_income),
        "total_expenses": dict(total_expenses),
        "net": net,
        "total_income_converted": round(total_income_converted, 2),
        "total_expenses_converted": round(total_expenses_converted, 2),
        "base_currency": base_currency,
    }


def _convert_total(
    totals: dict[str, float],
    base_currency: str,
    price_map: Any,
    price_date: datetime.date,
) -> float:
    """Convert a {currency: float} total to a scalar in base_currency."""
    result = 0.0
    for currency, amount in totals.items():
        if currency == base_currency:
            result += amount
        else:
            amt = Amount(Decimal(str(amount)), currency)
            converted = convert.convert_amount(amt, base_currency, price_map, price_date)
            if converted is not None and converted.currency == base_currency:
                result += float(converted.number)
    return result


def _period_bounds(
    year: int,
    month: int | None,
) -> tuple[datetime.date, datetime.date]:
    """Return (start_date inclusive, end_date exclusive) for the period."""
    if month is not None:
        start = datetime.date(year, month, 1)
        # End of month: first day of next month
        if month == 12:
            end = datetime.date(year + 1, 1, 1)
        else:
            end = datetime.date(year, month + 1, 1)
    else:
        start = datetime.date(year, 1, 1)
        end = datetime.date(year + 1, 1, 1)

    return start, end


def _base_currency(options: dict[str, Any]) -> str:
    """Determine the base currency from environment or options."""
    env_override = os.environ.get("BASE_CURRENCY")
    if env_override:
        return env_override.strip()
    oc = options.get("operating_currency", [])
    if oc:
        return oc[0]
    return "CHF"
