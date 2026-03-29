"""Tests for get_balances tool."""

from __future__ import annotations

import pytest

from mcp_beancount.allowlist import AllowList
from mcp_beancount.tools.balances import _matches, get_balances


def test_assets_prefix_returns_only_asset_accounts(entries, options):
    """Pattern 'Assets:' returns only accounts starting with Assets:."""
    result = get_balances(entries, options, "Assets:")
    assert len(result) > 0
    for item in result:
        assert item["account"].startswith("Assets:")


def test_checking_account_pattern_returns_single(entries, options):
    """Exact account name returns only that account."""
    result = get_balances(entries, options, "Assets:Bank:Checking")
    accounts = [item["account"] for item in result]
    assert all(a == "Assets:Bank:Checking" for a in accounts)
    assert len(result) >= 1


def test_wildcard_pattern_works(entries, options):
    """Glob pattern Assets:Bank:* matches bank accounts."""
    result = get_balances(entries, options, "Assets:Bank:*")
    assert len(result) > 0
    for item in result:
        assert item["account"].startswith("Assets:Bank:")


def test_nonmatching_pattern_returns_empty(entries, options):
    """Pattern with no matches returns empty list."""
    result = get_balances(entries, options, "Assets:Nonexistent:")
    assert result == []


def test_zero_balance_accounts_excluded(entries, options):
    """Accounts with zero balance are not returned."""
    result = get_balances(entries, options, "Assets:")
    for item in result:
        assert item["balance"] != 0.0


def test_returns_correct_balance_amounts(entries, options):
    """Returned balances are floats with currency strings."""
    result = get_balances(entries, options, "Assets:Bank:Savings")
    assert len(result) > 0
    for item in result:
        assert isinstance(item["balance"], float)
        assert isinstance(item["currency"], str)
        assert len(item["currency"]) == 3  # e.g. "CHF"


def test_allowlist_filters_out_non_matching(entries, options):
    """AllowList restricts to allowed prefixes only."""
    allowlist = AllowList(["Assets:Bank:Savings"])
    result = get_balances(entries, options, "Assets:", allowlist=allowlist)
    for item in result:
        assert item["account"].startswith("Assets:Bank:Savings")


def test_empty_allowlist_returns_all(entries, options):
    """Empty allowlist does not filter anything."""
    no_filter = AllowList([])
    result_no_filter = get_balances(entries, options, "Assets:")
    result_with_filter = get_balances(entries, options, "Assets:", allowlist=no_filter)
    assert len(result_no_filter) == len(result_with_filter)


# ── Tests — date filtering ────────────────────────────────────────────────────


def test_date_filter_excludes_later_transactions(entries, options):
    """Balances as of 2020-01-01 differ from all-time balances (ledger grows)."""
    result_all = get_balances(entries, options, "Assets:Bank:Checking")
    result_early = get_balances(entries, options, "Assets:Bank:Checking", date="2020-01-01")
    # The ledger has many transactions after 2020-01-01, so balances must differ
    all_balance = next(
        (item["balance"] for item in result_all if item["account"] == "Assets:Bank:Checking"), None
    )
    early_balance = next(
        (item["balance"] for item in result_early if item["account"] == "Assets:Bank:Checking"), None
    )
    assert all_balance != early_balance


def test_date_filter_iso_date(entries, options):
    """date='2026-01-01' returns a consistent, reproducible snapshot."""
    result = get_balances(entries, options, "Assets:Bank:Checking", date="2026-01-01")
    assert len(result) > 0
    for item in result:
        assert isinstance(item["balance"], float)


def test_date_filter_no_date_returns_all(entries, options):
    """No date parameter returns all transactions (existing behaviour)."""
    result_no_date = get_balances(entries, options, "Assets:")
    result_today = get_balances(entries, options, "Assets:")
    assert len(result_no_date) == len(result_today)


def test_date_filter_excludes_future_transactions(entries, options):
    """A very early date means only the opening balance is captured."""
    # The ledger opens on 2020-01-01; using that date captures only the opening txn
    result_opening = get_balances(entries, options, "Assets:Bank:Checking", date="2020-01-01")
    result_all = get_balances(entries, options, "Assets:Bank:Checking")
    # Opening balance should differ from final balance (transactions happened)
    opening_balance = next(
        (item["balance"] for item in result_opening if item["account"] == "Assets:Bank:Checking"), 0.0
    )
    all_balance = next(
        (item["balance"] for item in result_all if item["account"] == "Assets:Bank:Checking"), 0.0
    )
    # The opening balance in the sample is 15000 CHF; many transactions after that
    assert opening_balance != all_balance


# ── Tests — _matches() glob behaviour ────────────────────────────────────────


def test_glob_does_not_match_wrong_segment():
    """Assets:*:USD should NOT match Assets:Broker:EUR (issue #15)."""
    assert not _matches("Assets:Broker:EUR", "Assets:*:USD")


def test_glob_matches_correct_segment():
    """Assets:*:USD should match Assets:Broker:USD."""
    assert _matches("Assets:Broker:USD", "Assets:*:USD")


def test_glob_prefix_still_works():
    """Assets:Bank:* should match Assets:Bank:Checking."""
    assert _matches("Assets:Bank:Checking", "Assets:Bank:*")


def test_glob_prefix_does_not_match_other_account():
    """Assets:Bank:* should NOT match Assets:Savings:Checking."""
    assert not _matches("Assets:Savings:Checking", "Assets:Bank:*")
