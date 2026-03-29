"""Tests for get_transactions tool."""

from __future__ import annotations

import pytest

from mcp_beancount.tools.transactions import get_transactions, MAX_LIMIT


def test_no_filters_returns_transactions(entries, options):
    """No filters returns a list of transactions."""
    result = get_transactions(entries, options)
    assert isinstance(result, list)
    assert len(result) > 0


def test_default_limit_is_50(entries, options):
    """Default limit of 50 is applied."""
    result = get_transactions(entries, options)
    assert len(result) <= 50


def test_account_filter_works(entries, options):
    """account filter restricts to transactions involving that account."""
    result = get_transactions(entries, options, account="Expenses:Food")
    assert len(result) > 0
    for txn in result:
        accounts = [p["account"] for p in txn["postings"]]
        assert any(a == "Expenses:Food" or a.startswith("Expenses:Food:") for a in accounts)


def test_since_filter_works(entries, options):
    """since filter excludes older transactions."""
    result = get_transactions(entries, options, since="2026-01-01")
    for txn in result:
        assert txn["date"] >= "2026-01-01"


def test_limit_respected(entries, options):
    """Custom limit is respected."""
    result = get_transactions(entries, options, limit=5)
    assert len(result) <= 5


def test_limit_capped_at_200(entries, options):
    """limit is capped at MAX_LIMIT=200."""
    result = get_transactions(entries, options, limit=9999)
    assert len(result) <= MAX_LIMIT


def test_sorted_most_recent_first(entries, options):
    """Results are sorted by date descending."""
    result = get_transactions(entries, options, limit=20)
    dates = [txn["date"] for txn in result]
    assert dates == sorted(dates, reverse=True)


def test_posting_structure(entries, options):
    """Each posting has account, amount, and currency."""
    result = get_transactions(entries, options, limit=5)
    for txn in result:
        for posting in txn["postings"]:
            assert "account" in posting
            assert "amount" in posting
            assert "currency" in posting
            assert isinstance(posting["amount"], float)


def test_transaction_has_required_fields(entries, options):
    """Each transaction has date, flag, payee, narration, tags, links, postings."""
    result = get_transactions(entries, options, limit=3)
    for txn in result:
        assert "date" in txn
        assert "flag" in txn
        assert "payee" in txn
        assert "narration" in txn
        assert "tags" in txn
        assert "links" in txn
        assert "postings" in txn


# ── Tests — until parameter ───────────────────────────────────────────────────


def test_until_filter_excludes_later_transactions(entries, options):
    """until filter excludes transactions after the given date."""
    result = get_transactions(entries, options, until="2023-12-31", limit=200)
    for txn in result:
        assert txn["date"] <= "2023-12-31"


def test_until_filter_includes_on_date(entries, options):
    """until filter includes transactions on the exact date."""
    result = get_transactions(entries, options, until="2026-03-31", limit=200)
    dates = [txn["date"] for txn in result]
    # The ledger has a 2026-03-31 transaction; it must be included
    assert "2026-03-31" in dates


def test_since_and_until_together(entries, options):
    """since and until can be combined to define a date range."""
    result = get_transactions(entries, options, since="2026-01-01", until="2026-03-31", limit=200)
    for txn in result:
        assert "2026-01-01" <= txn["date"] <= "2026-03-31"


def test_until_with_no_matching_transactions(entries, options):
    """until before the first entry returns empty list."""
    result = get_transactions(entries, options, until="2019-12-31")
    assert result == []


def test_until_does_not_affect_ordering(entries, options):
    """Results are still sorted by date descending with until filter."""
    result = get_transactions(entries, options, until="2026-03-31", limit=20)
    dates = [txn["date"] for txn in result]
    assert dates == sorted(dates, reverse=True)
