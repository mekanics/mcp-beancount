"""get_net_worth tool — sum Assets and Liabilities at a given date."""

from __future__ import annotations

import datetime
import os
from collections import defaultdict
from typing import Any

from beancount.core import prices
from beancount.core.amount import Amount
from beancount.core.number import Decimal

from mcp_beancount.tools.utils import convert_chain, resolve_date


def get_net_worth(
    entries: list[Any],
    options: dict[str, Any],
    date: str | None = None,
) -> dict[str, Any]:
    """Compute net worth (assets minus liabilities) as of a given date.

    Uses beanquery to aggregate balances, which correctly handles synthetic
    entries from pad/balance directives and cost-lot positions.

    Args:
        entries: Beancount entries from loader.get().
        options: Beancount options dict.
        date: Date reference. Supported values:
              - None or "today" → today's date
              - "end-of-month"  → last day of the current month
              - ISO 8601 string (e.g. "2026-01-01") → that date

    Returns:
        dict with keys: as_of, base_currency, assets, liabilities,
        total_assets, total_liabilities, net_worth (all per-currency dicts),
        net_worth_converted (scalar in base_currency), skipped_positions.
    """
    # Determine cutoff date
    cutoff = resolve_date(date)

    # Determine base currency
    base_currency = _base_currency(options)

    # Build price map from price directives in the ledger
    price_map = prices.build_price_map(entries)

    # Use beanquery to get correct per-account balances (handles pad/balance synthetics)
    balances = _query_balances(entries, options, cutoff)

    # Build assets/liabilities dicts preserving per-currency breakdown
    assets: dict[str, dict[str, float]] = {}
    liabilities: dict[str, dict[str, float]] = {}

    for account, per_currency in balances.items():
        non_zero = {c: float(v) for c, v in per_currency.items() if v != 0}
        if not non_zero:
            continue
        if account.startswith("Assets:"):
            assets[account] = non_zero
        elif account.startswith("Liabilities:"):
            liabilities[account] = non_zero

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
            converted = convert_chain(amt, base_currency, price_map, cutoff)
            if converted is not None:
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


def _query_balances(
    entries: list[Any],
    options: dict[str, Any],
    cutoff: datetime.date,
) -> dict[str, dict[str, Decimal]]:
    """Use beanquery to get correct per-account, per-currency balances.

    This correctly handles synthetic entries from pad/balance directives
    and cost-lot positions (SUM(position) returns units currency).

    Args:
        entries: Beancount entries.
        options: Beancount options dict.
        cutoff: Date cutoff — only postings on or before this date are included.

    Returns:
        Mapping of account → {currency → Decimal balance}.
    """
    import beanquery
    from beanquery.sources.beancount import attach
    from beancount.parser.options import OPTIONS_DEFAULTS

    # beanquery requires a fully-populated options dict (needs name_assets etc.)
    # Merge defaults with whatever was provided so an empty dict still works.
    full_options = {**OPTIONS_DEFAULTS, **options}

    conn = beanquery.connect("")
    attach(conn, "beancount:", entries=entries, errors=[], options=full_options)

    bql = (
        "SELECT account, SUM(position) AS balance "
        "WHERE account ~ '^(Assets|Liabilities)' "
        f"AND date <= {cutoff.isoformat()} "
        "GROUP BY account"
    )
    cursor = conn.execute(bql)

    balances: dict[str, dict[str, Decimal]] = {}
    for row in cursor:
        account, inventory = row
        if inventory is None:
            continue
        per_currency: dict[str, Decimal] = defaultdict(Decimal)
        # Inventory is iterable yielding Position objects with .units (Amount)
        for position in inventory:
            per_currency[position.units.currency] += position.units.number
        balances[account] = dict(per_currency)

    return balances


def _base_currency(options: dict[str, Any]) -> str:
    """Determine the base currency from environment or options."""
    env_override = os.environ.get("BASE_CURRENCY")
    if env_override:
        return env_override.strip()
    oc = options.get("operating_currency", [])
    if oc:
        return oc[0]
    return "CHF"
