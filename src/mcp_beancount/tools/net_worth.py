"""get_net_worth tool — sum Assets and Liabilities at a given date."""

from __future__ import annotations

import datetime
import os
from collections import defaultdict
from typing import Any

from beancount.core import convert, prices
from beancount.core import data as beancount_data
from beancount.core.amount import Amount
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
        dict with keys: as_of, base_currency, assets, liabilities,
        total_assets, total_liabilities, net_worth (all per-currency dicts),
        net_worth_converted (scalar in base_currency), skipped_positions.
    """
    # Determine cutoff date
    cutoff = _parse_date(date) if date else _latest_date(entries)

    # Determine base currency
    base_currency = _base_currency(options)

    # Build price map from price directives in the ledger
    price_map = prices.build_price_map(entries)

    # Accumulate balances per account per currency
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

    # Build assets/liabilities dicts preserving per-currency breakdown
    assets: dict[str, dict[str, float]] = {}
    liabilities: dict[str, dict[str, float]] = {}

    for account, currencies in balances.items():
        per_currency = {c: float(v) for c, v in currencies.items() if v != 0}
        if not per_currency:
            continue
        if account.startswith("Assets:"):
            assets[account] = per_currency
        elif account.startswith("Liabilities:"):
            liabilities[account] = per_currency

    # Compute per-currency totals for assets
    total_assets: dict[str, float] = defaultdict(float)
    for per_currency in assets.values():
        for currency, amount in per_currency.items():
            total_assets[currency] += amount

    # Compute per-currency totals for liabilities
    total_liabilities: dict[str, float] = defaultdict(float)
    for per_currency in liabilities.values():
        for currency, amount in per_currency.items():
            total_liabilities[currency] += amount

    # Compute net worth per currency
    all_currencies = set(total_assets) | set(total_liabilities)
    net_worth_by_currency: dict[str, float] = {}
    for currency in all_currencies:
        net_worth_by_currency[currency] = round(
            total_assets.get(currency, 0.0) + total_liabilities.get(currency, 0.0), 2
        )

    # Compute net_worth_converted in base_currency using price_map
    net_worth_converted_total = 0.0
    skipped_positions: list[str] = []

    for currency, total in net_worth_by_currency.items():
        if currency == base_currency:
            net_worth_converted_total += total
        else:
            amt = Amount(Decimal(str(total)), currency)
            converted = convert.convert_amount(amt, base_currency, price_map, cutoff)
            if converted is not None and converted.currency == base_currency:
                net_worth_converted_total += float(converted.number)
            else:
                skipped_positions.append(currency)

    return {
        "as_of": cutoff.isoformat(),
        "base_currency": base_currency,
        "assets": assets,
        "liabilities": liabilities,
        "total_assets": dict(total_assets),
        "total_liabilities": dict(total_liabilities),
        "net_worth": net_worth_by_currency,
        "net_worth_converted": round(net_worth_converted_total, 2),
        "skipped_positions": skipped_positions,
    }


def _base_currency(options: dict[str, Any]) -> str:
    """Determine the base currency from environment or options."""
    env_override = os.environ.get("BASE_CURRENCY")
    if env_override:
        return env_override.strip()
    oc = options.get("operating_currency", [])
    if oc:
        return oc[0]
    return "CHF"


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
