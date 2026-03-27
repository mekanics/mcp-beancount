"""Tests for get_balances tool."""

from __future__ import annotations

import pytest

from mcp_beancount.allowlist import AllowList
from mcp_beancount.tools.balances import get_balances


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
