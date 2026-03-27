"""get_transactions tool — recent transactions with optional filters."""

from __future__ import annotations

import datetime
from typing import Any

from beancount.core import data as beancount_data

MAX_LIMIT = 200


def get_transactions(
    entries: list[Any],
    options: dict[str, Any],
    account: str | None = None,
    since: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return recent transactions, optionally filtered.

    Args:
        entries: Beancount entries from loader.get().
        options: Beancount options dict.
        account: Account name prefix filter (e.g. "Expenses:Food").
        since: ISO 8601 date string; only return transactions on/after this date.
        limit: Max number of transactions to return (capped at 200).

    Returns:
        List of transaction dicts sorted by date descending (most recent first).
    """
    effective_limit = min(max(limit, 1), MAX_LIMIT)
    since_date = datetime.date.fromisoformat(since) if since else None

    results: list[dict[str, Any]] = []

    for entry in entries:
        if not isinstance(entry, beancount_data.Transaction):
            continue
        if since_date and entry.date < since_date:
            continue
        if account and not _has_account(entry, account):
            continue

        results.append(_serialize_txn(entry))

    # Sort by date descending, then limit
    results.sort(key=lambda t: t["date"], reverse=True)
    return results[:effective_limit]


def _has_account(txn: beancount_data.Transaction, account_prefix: str) -> bool:
    """Return True if any posting in txn matches the account prefix."""
    for posting in txn.postings:
        if posting.account == account_prefix or posting.account.startswith(account_prefix + ":"):
            return True
    return False


def _serialize_txn(txn: beancount_data.Transaction) -> dict[str, Any]:
    """Serialize a beancount Transaction to a JSON-compatible dict."""
    postings = []
    for posting in txn.postings:
        if posting.units is not None:
            postings.append({
                "account": posting.account,
                "amount": float(round(posting.units.number, 2)),
                "currency": posting.units.currency,
            })

    return {
        "date": txn.date.isoformat(),
        "flag": txn.flag,
        "payee": txn.payee or "",
        "narration": txn.narration or "",
        "tags": sorted(txn.tags) if txn.tags else [],
        "links": sorted(txn.links) if txn.links else [],
        "postings": postings,
    }
