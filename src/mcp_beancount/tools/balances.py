"""get_balances tool — account balances matching a pattern."""

from __future__ import annotations

import fnmatch
from collections import defaultdict
from typing import Any

from beancount.core import data as beancount_data
from beancount.core.number import Decimal

from mcp_beancount.allowlist import AllowList


def get_balances(
    entries: list[Any],
    options: dict[str, Any],
    account_pattern: str,
    allowlist: AllowList | None = None,
) -> list[dict[str, Any]]:
    """Return non-zero account balances matching a pattern.

    Args:
        entries: Beancount entries from loader.get().
        options: Beancount options dict.
        account_pattern: Account prefix or glob pattern (e.g. "Assets:",
                         "Assets:Bank:*").
        allowlist: Optional AllowList to further restrict results.

    Returns:
        List of dicts: [{"account": str, "balance": float, "currency": str}]
        Accounts with zero balance are excluded.
    """
    if allowlist is None:
        allowlist = AllowList([])

    # Accumulate balances per account per currency
    balances: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

    for entry in entries:
        if not isinstance(entry, beancount_data.Transaction):
            continue
        for posting in entry.postings:
            account = posting.account
            if not _matches(account, account_pattern):
                continue
            if not allowlist.allows(account):
                continue
            if posting.units is not None:
                currency = posting.units.currency
                balances[account][currency] += posting.units.number

    result: list[dict[str, Any]] = []
    for account in sorted(balances.keys()):
        for currency, amount in balances[account].items():
            if amount == 0:
                continue
            result.append({
                "account": account,
                "balance": float(round(amount, 2)),
                "currency": currency,
            })

    return result


def _matches(account: str, pattern: str) -> bool:
    """Return True if account matches the pattern.

    Supports:
    - Prefix match: "Assets:" matches "Assets:Bank:Checking"
    - Exact match: "Assets:Bank:Checking"
    - Glob: "Assets:Bank:*" matches "Assets:Bank:Checking"
    """
    # If pattern ends with ":" it's a prefix
    if pattern.endswith(":"):
        return account.startswith(pattern)
    # If pattern contains "*" or "?", use fnmatch
    if "*" in pattern or "?" in pattern:
        return fnmatch.fnmatch(account, pattern) or account.startswith(pattern.rstrip("*"))
    # Otherwise: exact match or prefix
    return account == pattern or account.startswith(pattern + ":")
