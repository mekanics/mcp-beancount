"""get_net_worth tool — sum Assets and Liabilities at a given date."""

from __future__ import annotations

import datetime
from collections import defaultdict
from typing import Any

from beancount.core import data as beancount_data
from beancount.core.number import Decimal


def get_net_worth(
    entries: list[Any],
    options: dict[str, Any],
    date: str | None = None,
) -> dict[str, Any]:
    """Compute net worth (assets minus liabilities) as of a given date.

    Args:
        entries: Beancount entries from loader.get().
        options: Beancount options dict.
        date: ISO 8601 date string (e.g. "2026-01-01"). If None, uses the
              latest transaction date in the ledger.

    Returns:
        dict with keys: as_of, assets, liabilities, total_assets,
        total_liabilities, net_worth, currency.
    """
    # Determine cutoff date
    cutoff = _parse_date(date) if date else _latest_date(entries)

    # Accumulate balances per account
    balances: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

    for entry in entries:
        if not isinstance(entry, beancount_data.Transaction):
            continue
        if entry.date > cutoff:
            continue
        for posting in entry.postings:
            account = posting.account
            if not (account.startswith("Assets:") or account.startswith("Liabilities:")):
                continue
            if posting.units is not None:
                currency = posting.units.currency
                balances[account][currency] += posting.units.number

    # Determine primary currency
    primary_currency = _primary_currency(balances, "Assets:")

    # Build assets/liabilities dicts using primary currency only
    assets: dict[str, float] = {}
    liabilities: dict[str, float] = {}

    for account, currencies in balances.items():
        # Use primary currency if available, else first currency
        amount = float(
            currencies.get(primary_currency, next(iter(currencies.values()), Decimal(0)))
        )
        if amount == 0:
            continue
        if account.startswith("Assets:"):
            assets[account] = amount
        elif account.startswith("Liabilities:"):
            liabilities[account] = amount

    total_assets = sum(assets.values())
    total_liabilities = sum(liabilities.values())
    net_worth = total_assets + total_liabilities

    return {
        "as_of": cutoff.isoformat(),
        "assets": assets,
        "liabilities": liabilities,
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "net_worth": round(net_worth, 2),
        "currency": primary_currency,
    }


def _parse_date(date_str: str) -> datetime.date:
    """Parse ISO 8601 date string to datetime.date."""
    return datetime.date.fromisoformat(date_str)


def _latest_date(entries: list[Any]) -> datetime.date:
    """Return the latest transaction date in the ledger."""
    latest = datetime.date(2000, 1, 1)
    for entry in entries:
        if isinstance(entry, beancount_data.Transaction):
            if entry.date > latest:
                latest = entry.date
    return latest


def _primary_currency(
    balances: dict[str, dict[str, Decimal]],
    prefix: str,
) -> str:
    """Determine the most common currency in accounts matching prefix."""
    currency_count: dict[str, int] = defaultdict(int)
    for account, currencies in balances.items():
        if account.startswith(prefix):
            for currency in currencies:
                currency_count[currency] += 1
    if not currency_count:
        return "CHF"
    return max(currency_count, key=lambda c: currency_count[c])
