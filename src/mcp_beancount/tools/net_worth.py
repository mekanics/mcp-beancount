"""get_net_worth tool — sum Assets and Liabilities at a given date via BQL."""

from __future__ import annotations

import os
import re
from collections import defaultdict
from typing import Any

from mcp_beancount.tools.query import run_bql_query
from mcp_beancount.tools.utils import resolve_date


def get_net_worth(
    entries: list[Any],
    options: dict[str, Any],
    date: str | None = None,
) -> dict[str, Any]:
    """Compute net worth (assets minus liabilities) as of a given date.

    Uses BQL via beanquery for balance computation, which correctly handles
    all directive types (Transaction, Balance, Pad) and preserves cost basis.

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
    cutoff = resolve_date(date)
    base_currency = _base_currency(options)
    cutoff_iso = cutoff.isoformat()

    _zero_response = {
        "as_of": cutoff_iso,
        "base_currency": base_currency,
        "assets": {},
        "liabilities": {},
        "total_assets": {},
        "total_liabilities": {},
        "net_worth": {},
        "net_worth_converted": 0.0,
        "skipped_positions": [],
    }

    # ── Query 1: per-account balances ────────────────────────────────────────
    bql_breakdown = (
        f"SELECT account, "
        f"convert(value(sum(position), {cutoff_iso}), '{base_currency}') AS balance "
        f"WHERE (account ~ '^Assets' OR account ~ '^Liabilities') "
        f"AND date <= {cutoff_iso} "
        f"GROUP BY account "
        f"ORDER BY account"
    )

    breakdown_result = run_bql_query(entries, options, bql_breakdown)

    if "error" in breakdown_result or not breakdown_result.get("rows"):
        return _zero_response

    # ── Query 2: total net worth (single row) ────────────────────────────────
    bql_total = (
        f"SELECT convert(value(sum(position), {cutoff_iso}), '{base_currency}') AS net_worth "
        f"WHERE (account ~ '^Assets' OR account ~ '^Liabilities') "
        f"AND date <= {cutoff_iso}"
    )

    total_result = run_bql_query(entries, options, bql_total)

    # ── Parse per-account breakdown ──────────────────────────────────────────
    assets: dict[str, dict[str, float]] = {}
    liabilities: dict[str, dict[str, float]] = {}

    for row in breakdown_result["rows"]:
        account = row["account"]
        balance_str = row.get("balance", "")
        per_currency, _skipped = _parse_inventory(balance_str)

        # Remove zero balances
        per_currency = {c: v for c, v in per_currency.items() if v != 0}
        if not per_currency:
            continue

        if account.startswith("Assets:"):
            assets[account] = per_currency
        elif account.startswith("Liabilities:"):
            liabilities[account] = per_currency

    # ── Compute totals ────────────────────────────────────────────────────────
    total_assets: dict[str, float] = defaultdict(float)
    for per_currency in assets.values():
        for currency, amount in per_currency.items():
            total_assets[currency] += amount

    total_liabilities: dict[str, float] = defaultdict(float)
    for per_currency in liabilities.values():
        for currency, amount in per_currency.items():
            total_liabilities[currency] += amount

    # ── Net worth per currency ────────────────────────────────────────────────
    all_currencies = set(total_assets) | set(total_liabilities)
    net_worth_by_currency: dict[str, float] = {}
    for currency in all_currencies:
        nw = round(
            total_assets.get(currency, 0.0) + total_liabilities.get(currency, 0.0), 2
        )
        if nw != 0:
            net_worth_by_currency[currency] = nw

    # ── Parse total (net_worth_converted) ────────────────────────────────────
    net_worth_converted = 0.0
    skipped_positions: list[str] = []

    if total_result.get("rows"):
        total_inv_str = total_result["rows"][0].get("net_worth", "")
        total_positions, _skipped = _parse_inventory(total_inv_str)
        for currency, amount in total_positions.items():
            if currency == base_currency:
                net_worth_converted += amount
            else:
                skipped_positions.append(currency)

    return {
        "as_of": cutoff_iso,
        "base_currency": base_currency,
        "assets": assets,
        "liabilities": liabilities,
        "total_assets": dict(total_assets),
        "total_liabilities": dict(total_liabilities),
        "net_worth": net_worth_by_currency,
        "net_worth_converted": round(net_worth_converted, 2),
        "skipped_positions": sorted(set(skipped_positions)),
    }


def _parse_inventory(inventory_str: str) -> tuple[dict[str, float], list[str]]:
    """Parse a BQL serialized Inventory string into a per-currency float dict.

    Inventory strings from beanquery look like:
      ``(50000 CHF)``
      ``(26700.00 CHF)``
      ``(30000 USD, 50000 CHF)``
      ``(-2000 CHF)``

    Returns:
        Tuple of (per_currency_dict, skipped_parts) where skipped_parts
        contains position strings that could not be parsed.
    """
    if not inventory_str:
        return {}, []

    s = inventory_str.strip()
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()

    if not s:
        return {}, []

    result: dict[str, float] = {}
    skipped: list[str] = []

    for part in s.split(","):
        part = part.strip()
        m = re.match(r"^(-?[0-9]+(?:\.[0-9]+)?)\s+([A-Z][A-Z0-9_.~-]{0,22})$", part)
        if m:
            number = float(m.group(1))
            currency = m.group(2)
            result[currency] = result.get(currency, 0.0) + number
        elif part:
            skipped.append(part)

    return result, skipped


def _base_currency(options: dict[str, Any]) -> str:
    """Determine the base currency from environment or options."""
    env_override = os.environ.get("BASE_CURRENCY")
    if env_override:
        return env_override.strip()
    oc = options.get("operating_currency", [])
    if oc:
        return oc[0]
    return "CHF"
