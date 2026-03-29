"""Shared utilities for mcp-beancount tools."""

from __future__ import annotations

import calendar
import datetime

from beancount.core import convert
from beancount.core.amount import Amount


def convert_chain(
    amt: Amount,
    target: str,
    price_map: object,
    date: datetime.date | None = None,
    max_hops: int = 3,
) -> Amount | None:
    """Convert amt to target currency, chaining through intermediaries if needed.

    - Hop 0: direct (amt.currency → target)
    - Hop 1: single intermediary via price_map key discovery
    - Hop 2: 3-hop chain (rare, e.g. VT→USD→EUR→CHF)

    Args:
        amt: The amount to convert.
        target: The target currency code.
        price_map: Beancount price map built from price directives.
        date: Date for price lookup (None = latest available).
        max_hops: Maximum number of conversion hops (default 3).

    Returns:
        Converted Amount in target currency, or None if no path found.
    """
    if amt.currency == target:
        return amt

    # Hop 0: direct
    result = convert.convert_amount(amt, target, price_map, date)
    if result.currency == target:
        return result

    if max_hops < 2:
        return None

    # Discover intermediaries from price_map keys
    intermediaries: set[str] = set()
    for base, quote in price_map.keys():
        if base == amt.currency:
            intermediaries.add(quote)
        if quote == amt.currency:
            intermediaries.add(base)
    intermediaries.discard(target)
    intermediaries.discard(amt.currency)

    # Hop 1: 2-hop via each intermediary
    for mid in intermediaries:
        result = convert.convert_amount(amt, target, price_map, date, via=(mid,))
        if result.currency == target:
            return result

    # Hop 2: 3-hop via two intermediaries
    if max_hops >= 3:
        for mid1 in intermediaries:
            step1 = convert.convert_amount(amt, mid1, price_map, date)
            if step1.currency != mid1:
                continue
            step2 = convert_chain(step1, target, price_map, date, max_hops=1)
            if step2 is not None and step2.currency == target:
                return step2

    return None


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
