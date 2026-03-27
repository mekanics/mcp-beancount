"""get_income_statement tool — income vs expenses for a period."""

from __future__ import annotations

import datetime
from collections import defaultdict
from typing import Any

from beancount.core import data as beancount_data
from beancount.core.number import Decimal


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
        dict with: period, total_income, total_expenses, net,
                   income_breakdown, expense_breakdown.
    """
    start_date, end_date = _period_bounds(year, month)

    income_breakdown: dict[str, float] = defaultdict(float)
    expense_breakdown: dict[str, float] = defaultdict(float)

    for entry in entries:
        if not isinstance(entry, beancount_data.Transaction):
            continue
        if not (start_date <= entry.date < end_date):
            continue
        for posting in entry.postings:
            account = posting.account
            if posting.units is None:
                continue
            amount = float(posting.units.number)
            if account.startswith("Income:"):
                # Income is stored as negative in beancount; negate for display
                income_breakdown[account] += -amount
            elif account.startswith("Expenses:"):
                expense_breakdown[account] += amount

    # Round values
    income_breakdown = {k: round(v, 2) for k, v in income_breakdown.items()}
    expense_breakdown = {k: round(v, 2) for k, v in expense_breakdown.items()}

    total_income = round(sum(income_breakdown.values()), 2)
    total_expenses = round(sum(expense_breakdown.values()), 2)
    net = round(total_income - total_expenses, 2)

    period = f"{year:04d}-{month:02d}" if month else f"{year:04d}"

    return {
        "period": period,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net": net,
        "income_breakdown": dict(income_breakdown),
        "expense_breakdown": dict(expense_breakdown),
    }


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
