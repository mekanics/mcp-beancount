"""Shared utilities for mcp-beancount tools."""

from __future__ import annotations

import calendar
import datetime


def resolve_date(date_str: str | None) -> datetime.date:
    """Resolve a date string to a datetime.date.

    Supported values:
        None          → today
        "today"       → today
        "end-of-month" → last day of the current month
        ISO 8601 str  → parsed with datetime.date.fromisoformat()

    Args:
        date_str: Date string or None.

    Returns:
        Resolved datetime.date.
    """
    if date_str is None or date_str == "today":
        return datetime.date.today()
    if date_str == "end-of-month":
        today = datetime.date.today()
        last_day = calendar.monthrange(today.year, today.month)[1]
        return datetime.date(today.year, today.month, last_day)
    return datetime.date.fromisoformat(date_str)
